package com.cura.android

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
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
        if (ContextCompat.checkSelfPermission(
                this, android.Manifest.permission.RECORD_AUDIO
            ) != PackageManager.PERMISSION_GRANTED
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
        worker = Thread({
            val minBuffer = AudioRecord.getMinBufferSize(
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT
            )
            if (minBuffer <= 0) {
                Log.e(TAG, "Android could not determine an audio buffer size: $minBuffer")
                stopSelf()
                return@Thread
            }
            var audio: AudioRecord? = null
            try {
                val capture = AudioRecord(
                    MediaRecorder.AudioSource.MIC,
                    SAMPLE_RATE,
                    AudioFormat.CHANNEL_IN_MONO,
                    AudioFormat.ENCODING_PCM_16BIT,
                    maxOf(minBuffer, SAMPLE_COUNT * 2)
                )
                audio = capture
                recorder = capture
                capture.startRecording()
                getSharedPreferences(CuraAndroidPlugin.PREFS, Context.MODE_PRIVATE)
                    .edit().putBoolean(CuraAndroidPlugin.MIC_ACTIVE, true).apply()
                val samples = ShortArray(SAMPLE_COUNT)
                while (!stopping && capture.recordingState == AudioRecord.RECORDSTATE_RECORDING) {
                    val count = capture.read(samples, 0, samples.size)
                    if (count == AudioRecord.ERROR_DEAD_OBJECT) {
                        Log.e(TAG, "AudioRecord became unavailable.")
                        break
                    }
                    if (count > 0) {
                        var sum = 0.0
                        for (i in 0 until count) {
                            val normalized = samples[i].toDouble() / 32768.0
                            sum += normalized * normalized
                        }
                        val rms = sqrt(sum / count)
                        val dbfs = if (rms <= 0.00003) -90.0 else (20.0 * log10(rms)).coerceAtLeast(-90.0)
                        var peak = 0.0
                        for (i in 0 until count) {
                            peak = maxOf(peak, kotlin.math.abs(samples[i].toDouble() / 32768.0))
                        }
                        val prefs = getSharedPreferences(CuraAndroidPlugin.PREFS, Context.MODE_PRIVATE)
                        prefs.edit().putFloat(CuraAndroidPlugin.MIC_LEVEL, dbfs.toFloat()).apply()
                        val alertActive = prefs.getBoolean(ALERT_ACTIVE, false)
                        val triggered = !alertActive &&
                            (rms >= RMS_THRESHOLD ||
                                (peak >= PEAK_THRESHOLD && rms >= PEAK_MIN_RMS))
                        if (triggered) {
                            prefs.edit()
                                .putBoolean(ALERT_ACTIVE, true)
                                .putBoolean(CuraAndroidPlugin.PENDING_AUDIO_ALERT, true)
                                .apply()
                            AudioAlertNotifications.show(this@MicrophoneMonitorService, dbfs)
                        } else if (alertActive && rms <= RESET_THRESHOLD) {
                            prefs.edit().putBoolean(ALERT_ACTIVE, false).apply()
                        }
                        val now = System.currentTimeMillis()
                        if (now - lastNotificationAt >= NOTIFICATION_REFRESH_MS) {
                            lastNotificationAt = now
                            getSystemService(NotificationManager::class.java)
                                .notify(NOTIFICATION_ID, buildNotification(dbfs))
                        }
                    }
                }
            } catch (_: IllegalStateException) {
                Log.e(TAG, "Microphone capture stopped unexpectedly.")
                stopSelf()
            } catch (error: SecurityException) {
                Log.e(TAG, "Android denied microphone capture.", error)
                stopSelf()
            } finally {
                audio?.let { capture ->
                    try {
                        if (capture.recordingState == AudioRecord.RECORDSTATE_RECORDING) {
                            capture.stop()
                        }
                    } catch (error: IllegalStateException) {
                        Log.w(TAG, "AudioRecord was already stopped.", error)
                    }
                    capture.release()
                }
                recorder = null
                getSharedPreferences(CuraAndroidPlugin.PREFS, Context.MODE_PRIVATE)
                    .edit().putBoolean(CuraAndroidPlugin.MIC_ACTIVE, false).apply()
                stopSelf()
            }
        }, "cura-microphone-monitor").apply { start() }
    }

    private fun buildNotification(dbfs: Double): Notification =
        NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("CURA microphone monitoring")
            .setContentText("Listening is active · ${"%.0f".format(dbfs)} dBFS")
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "CURA microphone monitoring",
                NotificationManager.IMPORTANCE_LOW
            ).apply { description = "Visible notice while microphone monitoring is active." }
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        stopping = true
        try {
            recorder?.stop()
        } catch (_: IllegalStateException) { }
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
        private const val SAMPLE_COUNT = 2048
        private const val NOTIFICATION_REFRESH_MS = 5000L
        private const val RMS_THRESHOLD = 0.025
        private const val PEAK_THRESHOLD = 0.45
        private const val PEAK_MIN_RMS = 0.012
        private const val RESET_THRESHOLD = 0.01
        private const val ALERT_ACTIVE = "microphone_alert_active"
    }
}
