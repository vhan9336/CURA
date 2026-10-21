package com.cura.android

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.MediaRecorder
import android.media.audiofx.AutomaticGainControl
import android.media.audiofx.NoiseSuppressor
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import org.tensorflow.lite.task.audio.classifier.AudioClassifier
import org.tensorflow.lite.task.core.BaseOptions
import org.tensorflow.lite.support.audio.TensorAudio
import kotlin.math.log10
import kotlin.math.sqrt

class MicrophoneMonitorService : Service() {
    @Volatile private var recorder: AudioRecord? = null
    @Volatile private var worker: Thread? = null
    @Volatile private var stopping = false
    private var lastNotificationAt = 0L

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.RECORD_AUDIO) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            stopSelf()
            return START_NOT_STICKY
        }
        startForeground(NOTIFICATION_ID, buildNotification(-90.0))
        if (worker?.isAlive != true) startCapture()
        return START_STICKY
    }

    private fun startCapture() {
        stopping = false
        worker = Thread({ captureLoop() }, "cura-microphone-monitor").apply { start() }
    }

    private fun captureLoop() {
        var audio: AudioRecord? = null
        var classifier: AudioClassifier? = null
        var agc: AutomaticGainControl? = null
        var noiseSuppressor: NoiseSuppressor? = null
        try {
            val options = AudioClassifier.AudioClassifierOptions.builder()
                .setBaseOptions(BaseOptions.builder().setNumThreads(2).build())
                .setMaxResults(CLASS_COUNT)
                .setScoreThreshold(0f)
                .build()
            classifier = AudioClassifier.createFromFileAndOptions(this, MODEL_FILE, options)
            val tensorAudio = classifier.createInputTensorAudio()
            val minBuffer = AudioRecord.getMinBufferSize(
                SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT
            )
            if (minBuffer <= 0) throw IllegalStateException("Invalid AudioRecord buffer size: $minBuffer")

            val source = preferredAudioSource()
            val capture = AudioRecord(
                source, SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                maxOf(minBuffer, READ_SAMPLE_COUNT * 4)
            )
            audio = capture
            recorder = capture
            if (capture.state != AudioRecord.STATE_INITIALIZED) {
                throw IllegalStateException("AudioRecord failed to initialize (source=$source)")
            }
            if (AutomaticGainControl.isAvailable()) {
                agc = runCatching { AutomaticGainControl.create(capture.audioSessionId)?.apply { enabled = false } }
                    .onFailure { Log.w(TAG, "Could not disable device AGC", it) }.getOrNull()
            }
            if (NoiseSuppressor.isAvailable()) {
                noiseSuppressor = runCatching { NoiseSuppressor.create(capture.audioSessionId)?.apply { enabled = false } }
                    .onFailure { Log.w(TAG, "Could not disable noise suppression", it) }.getOrNull()
            }

            capture.startRecording()
            getSharedPreferences(CuraAndroidPlugin.PREFS, Context.MODE_PRIVATE)
                .edit().putBoolean(CuraAndroidPlugin.MIC_ACTIVE, true).apply()

            val frame = ShortArray(READ_SAMPLE_COUNT)
            val modelWindow = ShortArray(MODEL_WINDOW_SAMPLES)
            var modelSamples = 0
            var noiseFloorDbfs = INITIAL_NOISE_FLOOR_DBFS
            var candidateUntil = 0L
            var loudScreamWindows = 0
            var lastAlertAt = 0L
            var lastMeterUpdateAt = 0L

            while (!stopping && capture.recordingState == AudioRecord.RECORDSTATE_RECORDING) {
                val count = capture.read(frame, 0, frame.size)
                if (count == AudioRecord.ERROR_DEAD_OBJECT) {
                    Log.e(TAG, "AudioRecord became unavailable.")
                    break
                }
                if (count <= 0) continue

                val levels = levels(frame, count)
                val dbfs = levels.first
                val peakDbfs = levels.second
                val oldFloor = noiseFloorDbfs
                val impulseCandidate = dbfs >= maxOf(IMPULSE_RMS_MIN_DBFS, oldFloor + IMPULSE_RMS_MARGIN_DB) &&
                    peakDbfs >= maxOf(IMPULSE_PEAK_MIN_DBFS, oldFloor + IMPULSE_PEAK_MARGIN_DB) &&
                    (peakDbfs - dbfs >= IMPULSE_CREST_DB || dbfs - oldFloor >= IMPULSE_RISE_DB)
                if (impulseCandidate) candidateUntil = System.currentTimeMillis() + IMPULSE_LOOKBACK_MS
                else if (dbfs < oldFloor + NOISE_UPDATE_GUARD_DB) {
                    noiseFloorDbfs = (oldFloor + (dbfs - oldFloor) * NOISE_FLOOR_ALPHA)
                        .coerceIn(MIN_NOISE_FLOOR_DBFS, MAX_NOISE_FLOOR_DBFS)
                } else if (dbfs < oldFloor + NOISE_RISE_LIMIT_DB) {
                    noiseFloorDbfs = (oldFloor + (dbfs - oldFloor) * NOISE_RISE_ALPHA)
                        .coerceIn(MIN_NOISE_FLOOR_DBFS, MAX_NOISE_FLOOR_DBFS)
                }

                val prefs = getSharedPreferences(CuraAndroidPlugin.PREFS, Context.MODE_PRIVATE)
                val now = System.currentTimeMillis()
                if (now - lastMeterUpdateAt >= METER_UPDATE_MS) {
                    prefs.edit().putFloat(CuraAndroidPlugin.MIC_LEVEL, dbfs.toFloat()).apply()
                    lastMeterUpdateAt = now
                }
                var frameOffset = 0
                while (frameOffset < count) {
                    val copied = minOf(count - frameOffset, MODEL_WINDOW_SAMPLES - modelSamples)
                    System.arraycopy(frame, frameOffset, modelWindow, modelSamples, copied)
                    modelSamples += copied
                    frameOffset += copied
                    if (modelSamples == MODEL_WINDOW_SAMPLES) {
                        val windowDbfs = levels(modelWindow, modelWindow.size).first
                        tensorAudio.load(modelWindow)
                        val scores = classifier.classify(tensorAudio)
                            .flatMap { it.categories }
                            .associate { it.label.trim().lowercase() to it.score }
                        val impactScore = maxScore(scores, IMPACT_LABELS)
                        val screamScore = maxScore(scores, SCREAM_LABELS)
                        val impulseRecent = now <= candidateUntil
                        val impactDetected = (impulseRecent && impactScore >= IMPACT_SCORE_THRESHOLD) ||
                            impactScore >= STRONG_IMPACT_SCORE_THRESHOLD
                        val screamEnergetic = windowDbfs >=
                            maxOf(SCREAM_MIN_DBFS, noiseFloorDbfs + SCREAM_RMS_MARGIN_DB)
                        loudScreamWindows = if (screamEnergetic && screamScore >= SCREAM_SCORE_THRESHOLD) {
                            loudScreamWindows + 1
                        } else 0
                        val screamDetected = screamEnergetic &&
                            (screamScore >= STRONG_SCREAM_SCORE_THRESHOLD || loudScreamWindows >= REQUIRED_SCREAM_WINDOWS)
                        if (!prefs.getBoolean(ALERT_ACTIVE, false) && (impactDetected || screamDetected) &&
                            now - lastAlertAt >= ALERT_COOLDOWN_MS
                        ) {
                            prefs.edit().putBoolean(ALERT_ACTIVE, true)
                                .putBoolean(CuraAndroidPlugin.PENDING_AUDIO_ALERT, true).apply()
                            AudioAlertNotifications.show(this@MicrophoneMonitorService, dbfs)
                            lastAlertAt = now
                        }
                        val remaining = modelSamples - MODEL_HOP_SAMPLES
                        System.arraycopy(modelWindow, MODEL_HOP_SAMPLES, modelWindow, 0, remaining)
                        modelSamples = remaining
                    }
                }

                if (prefs.getBoolean(ALERT_ACTIVE, false) &&
                    dbfs < maxOf(REARM_MAX_DBFS, noiseFloorDbfs + REARM_NOISE_MARGIN_DB)
                ) {
                    if (quietSince == 0L) quietSince = now
                    if (now - quietSince >= REARM_QUIET_MS) {
                        prefs.edit().putBoolean(ALERT_ACTIVE, false).apply()
                        quietSince = 0L
                    }
                } else quietSince = 0L

                if (now - lastNotificationAt >= NOTIFICATION_REFRESH_MS) {
                    lastNotificationAt = now
                    getSystemService(NotificationManager::class.java)
                        .notify(NOTIFICATION_ID, buildNotification(dbfs))
                }
            }
        } catch (error: IllegalStateException) {
            Log.e(TAG, "Microphone capture or audio classifier stopped unexpectedly.", error)
            stopSelf()
        } catch (error: SecurityException) {
            Log.e(TAG, "Android denied microphone capture.", error)
            stopSelf()
        } catch (error: Exception) {
            Log.e(TAG, "Could not initialize on-device sound classification.", error)
            stopSelf()
        } finally {
            runCatching { agc?.release() }
            runCatching { noiseSuppressor?.release() }
            audio?.let { capture ->
                runCatching { if (capture.recordingState == AudioRecord.RECORDSTATE_RECORDING) capture.stop() }
                capture.release()
            }
            classifier?.close()
            recorder = null
            getSharedPreferences(CuraAndroidPlugin.PREFS, Context.MODE_PRIVATE)
                .edit().putBoolean(CuraAndroidPlugin.MIC_ACTIVE, false).apply()
            stopSelf()
        }
    }

    @Volatile private var quietSince = 0L

    private fun preferredAudioSource(): Int {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            val audioManager = getSystemService(AudioManager::class.java)
            if (audioManager.getProperty(AudioManager.PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED) == "true") {
                return MediaRecorder.AudioSource.UNPROCESSED
            }
        }
        return MediaRecorder.AudioSource.VOICE_RECOGNITION
    }

    private fun levels(samples: ShortArray, count: Int): Pair<Double, Double> {
        var sum = 0.0
        var peak = 0.0
        for (i in 0 until count) {
            val normalized = samples[i].toDouble() / 32768.0
            sum += normalized * normalized
            peak = maxOf(peak, kotlin.math.abs(normalized))
        }
        val rms = sqrt(sum / count)
        return toDbfs(rms) to toDbfs(peak)
    }

    private fun toDbfs(value: Double): Double =
        if (value <= 0.00003) -90.0 else (20.0 * log10(value)).coerceAtLeast(-90.0)

    private fun maxScore(scores: Map<String, Float>, labels: Set<String>): Float =
        labels.maxOfOrNull { target -> scores.filterKeys { key -> key == target || key.startsWith("$target,") }
            .values.maxOrNull() ?: 0f } ?: 0f

    private fun buildNotification(dbfs: Double): Notification =
        NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("CURA microphone monitoring")
            .setContentText("Listening is active · ${"%.0f".format(dbfs)} dBFS")
            .setOngoing(true).setOnlyAlertOnce(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setPriority(NotificationCompat.PRIORITY_LOW).build()

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            val channel = NotificationChannel(CHANNEL_ID, "CURA microphone monitoring", NotificationManager.IMPORTANCE_LOW)
                .apply { description = "Visible notice while microphone monitoring is active." }
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        stopping = true
        runCatching { recorder?.stop() }
        worker?.join(500)
        stopForeground(STOP_FOREGROUND_REMOVE)
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val TAG = "CuraMicMonitor"
        const val ACTION_START = "com.cura.android.START_MONITORING"
        private const val CHANNEL_ID = "cura_microphone_monitor"
        private const val NOTIFICATION_ID = 7311
        private const val SAMPLE_RATE = 16000
        private const val READ_SAMPLE_COUNT = 160 // 10 ms frames keep impact timing precise.
        private const val MODEL_WINDOW_SAMPLES = 15600 // YAMNet's 0.975 s input window.
        private const val MODEL_HOP_SAMPLES = 7680 // 0.48 s overlap between classifications.
        private const val CLASS_COUNT = 521
        private const val MODEL_FILE = "yamnet.tflite"
        private const val NOTIFICATION_REFRESH_MS = 5000L
        private const val METER_UPDATE_MS = 150L
        private const val IMPULSE_LOOKBACK_MS = 1500L
        private const val ALERT_COOLDOWN_MS = 1500L
        private const val REARM_QUIET_MS = 1800L
        private const val INITIAL_NOISE_FLOOR_DBFS = -55.0
        private const val MIN_NOISE_FLOOR_DBFS = -80.0
        private const val MAX_NOISE_FLOOR_DBFS = -22.0
        private const val NOISE_FLOOR_ALPHA = 0.04
        private const val NOISE_RISE_ALPHA = 0.001
        private const val NOISE_UPDATE_GUARD_DB = 4.0
        private const val NOISE_RISE_LIMIT_DB = 18.0
        private const val IMPULSE_RMS_MIN_DBFS = -45.0
        private const val IMPULSE_RMS_MARGIN_DB = 9.0
        private const val IMPULSE_PEAK_MIN_DBFS = -20.0
        private const val IMPULSE_PEAK_MARGIN_DB = 18.0
        private const val IMPULSE_CREST_DB = 12.0
        private const val IMPULSE_RISE_DB = 7.0
        private const val IMPACT_SCORE_THRESHOLD = 0.25f
        private const val STRONG_IMPACT_SCORE_THRESHOLD = 0.65f
        private const val SCREAM_SCORE_THRESHOLD = 0.35f
        private const val STRONG_SCREAM_SCORE_THRESHOLD = 0.70f
        private const val REQUIRED_SCREAM_WINDOWS = 2
        private const val SCREAM_MIN_DBFS = -48.0
        private const val SCREAM_RMS_MARGIN_DB = 5.0
        private const val REARM_MAX_DBFS = -48.0
        private const val REARM_NOISE_MARGIN_DB = 3.0
        private const val ALERT_ACTIVE = "microphone_alert_active"
        private val IMPACT_LABELS = setOf("explosion", "smash, crash", "breaking", "gunshot, gunfire", "firecracker")
        private val SCREAM_LABELS = setOf("screaming", "shout", "yell")
    }
}
