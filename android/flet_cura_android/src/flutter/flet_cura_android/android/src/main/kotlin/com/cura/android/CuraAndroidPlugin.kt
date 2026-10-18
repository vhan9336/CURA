package com.cura.android

import android.Manifest
import android.app.Activity
import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.embedding.engine.plugins.activity.ActivityAware
import io.flutter.embedding.engine.plugins.activity.ActivityPluginBinding
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugin.common.PluginRegistry.RequestPermissionsResultListener

class CuraAndroidPlugin : FlutterPlugin, MethodChannel.MethodCallHandler,
    ActivityAware, RequestPermissionsResultListener {

    private lateinit var appContext: Context
    private var channel: MethodChannel? = null
    private var activity: Activity? = null
    private var activityBinding: ActivityPluginBinding? = null
    private var permissionResult: MethodChannel.Result? = null

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        appContext = binding.applicationContext
        channel = MethodChannel(binding.binaryMessenger, CHANNEL).also {
            it.setMethodCallHandler(this)
        }
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        try {
            when (call.method) {
                "requestPermissions" -> requestPermissions(result)
                "startMonitoring" -> startMonitoring(result)
                "stopMonitoring" -> {
                    appContext.stopService(
                        Intent(appContext, MicrophoneMonitorService::class.java)
                    )
                    result.success(null)
                }
                "microphoneLevel" -> {
                    val prefs = appContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                    result.success(
                        if (prefs.getBoolean(MIC_ACTIVE, false)) {
                            prefs.getFloat(MIC_LEVEL, -90f).toDouble()
                        } else {
                            null
                        }
                    )
                }
                "consumeAudioAlert" -> result.success(consumePending(PENDING_AUDIO_ALERT))
                "consumeCheckin" -> result.success(consumePending(PENDING_CHECKIN))
                "scheduleCheckins" -> scheduleCheckins(call, result)
                "cancelCheckins" -> {
                    CheckinScheduling.cancel(appContext)
                    result.success(null)
                }
                else -> result.notImplemented()
            }
        } catch (error: Exception) {
            result.error("cura_android_error", error.message ?: error.javaClass.simpleName, null)
        }
    }

    private fun consumePending(key: String): Boolean {
        val prefs = appContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val pending = prefs.getBoolean(key, false)
        if (pending) prefs.edit().putBoolean(key, false).apply()
        return pending
    }

    private fun requestPermissions(result: MethodChannel.Result) {
        val currentActivity = activity
        if (currentActivity == null) {
            result.error("activity_unavailable", "Open CURA before requesting permissions.", null)
            return
        }

        val requested = mutableListOf(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= 33) {
            requested.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        val missing = requested.filter {
            ContextCompat.checkSelfPermission(currentActivity, it) !=
                PackageManager.PERMISSION_GRANTED
        }
        if (missing.isEmpty()) {
            result.success(permissionStatus(currentActivity))
            return
        }
        if (permissionResult != null) {
            result.error("permission_request_in_progress", "Permission request already active.", null)
            return
        }
        permissionResult = result
        ActivityCompat.requestPermissions(currentActivity, missing.toTypedArray(), PERMISSION_REQUEST)
    }

    private fun startMonitoring(result: MethodChannel.Result) {
        val currentActivity = activity
        if (currentActivity == null || !isForeground(currentActivity)) {
            result.error(
                "foreground_required",
                "Start microphone monitoring from CURA while it is visible.",
                null
            )
            return
        }
        if (ContextCompat.checkSelfPermission(
                appContext, Manifest.permission.RECORD_AUDIO
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            result.error("microphone_permission_required", "Request microphone permission first.", null)
            return
        }
        val intent = Intent(appContext, MicrophoneMonitorService::class.java)
            .setAction(MicrophoneMonitorService.ACTION_START)
        ContextCompat.startForegroundService(appContext, intent)
        result.success(null)
    }

    private fun scheduleCheckins(call: MethodCall, result: MethodChannel.Result) {
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(
                appContext, Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            result.error("notification_permission_required", "Request notification permission first.", null)
            return
        }
        val wake = call.argument<String>("wake") ?: error("Missing wake time")
        val bed = call.argument<String>("bed") ?: error("Missing bed time")
        val (wakeMinute, bedMinute) = Pair(parseMinute(wake), parseMinute(bed))
        if (wakeMinute == bedMinute) {
            CheckinScheduling.cancel(appContext)
            result.success(
                mapOf("scheduled" to false, "limitation" to "Wake and bed times match; check-ins are disabled.")
            )
            return
        }
        CheckinScheduling.saveAndSchedule(appContext, wakeMinute, bedMinute)
        result.success(
            mapOf(
                "scheduled" to true,
                "accuracy" to "inexact",
                "limitation" to "Android may defer inexact alarms, especially in Doze mode."
            )
        )
    }

    private fun parseMinute(value: String): Int {
        val parts = value.split(":")
        require(parts.size == 2)
        val hour = parts[0].toInt()
        val minute = parts[1].toInt()
        require(hour in 0..23 && minute in 0..59) { "Time must be HH:MM." }
        return hour * 60 + minute
    }

    private fun permissionStatus(context: Context): Map<String, Boolean> = mapOf(
        "microphone" to (ContextCompat.checkSelfPermission(
            context, Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED),
        "notifications" to (Build.VERSION.SDK_INT < 33 ||
            ContextCompat.checkSelfPermission(
                context, Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED)
    )

    private fun isForeground(currentActivity: Activity): Boolean {
        if (currentActivity.isFinishing || !currentActivity.window.decorView.hasWindowFocus()) {
            return false
        }
        val manager = currentActivity.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val process = manager.runningAppProcesses?.firstOrNull {
            it.processName == currentActivity.packageName
        }
        return process?.importance == ActivityManager.RunningAppProcessInfo.IMPORTANCE_FOREGROUND
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ): Boolean {
        if (requestCode != PERMISSION_REQUEST) return false
        permissionResult?.success(permissionStatus(appContext))
        permissionResult = null
        return true
    }

    override fun onAttachedToActivity(binding: ActivityPluginBinding) {
        activity = binding.activity
        activityBinding = binding
        binding.addRequestPermissionsResultListener(this)
    }

    override fun onDetachedFromActivityForConfigChanges() = detachActivity()
    override fun onReattachedToActivityForConfigChanges(binding: ActivityPluginBinding) =
        onAttachedToActivity(binding)
    override fun onDetachedFromActivity() = detachActivity()

    private fun detachActivity() {
        permissionResult?.error("activity_unavailable", "Activity was detached.", null)
        permissionResult = null
        activityBinding?.removeRequestPermissionsResultListener(this)
        activityBinding = null
        activity = null
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel?.setMethodCallHandler(null)
        channel = null
    }

    companion object {
        private const val CHANNEL = "com.cura.android/native"
        private const val PERMISSION_REQUEST = 7184
        const val PREFS = "cura_android_native"
        const val MIC_ACTIVE = "microphone_active"
        const val MIC_LEVEL = "microphone_level_dbfs"
        const val PENDING_AUDIO_ALERT = "pending_audio_alert"
        const val PENDING_CHECKIN = "pending_checkin"
    }
}
