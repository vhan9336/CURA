package com.cura.android

import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import java.util.Calendar

class CheckinAlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        if (CheckinScheduling.isAwake(context, Calendar.getInstance())) {
            CheckinNotifications.show(context)
        }
        CheckinScheduling.scheduleNext(context)
    }
}

class CheckinRestoreReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        CheckinScheduling.scheduleNext(context)
    }
}

internal object CheckinNotifications {
    private const val CHANNEL_ID = "cura_local_checkins"
    private const val NOTIFICATION_ID = 7312

    fun show(context: Context) {
        context.getSharedPreferences(CuraAndroidPlugin.PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean(CuraAndroidPlugin.PENDING_CHECKIN, true).apply()
        val manager = context.getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= 26) {
            manager.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    "CURA check-ins",
                    NotificationManager.IMPORTANCE_DEFAULT
                )
            )
        }
        manager.notify(
            NOTIFICATION_ID,
            NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("How are you doing?")
                .setContentText("Take a moment for your CURA check-in.")
                .setContentIntent(openApp(context, 7312))
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .build()
        )
    }
}

internal object AudioAlertNotifications {
    private const val CHANNEL_ID = "cura_sound_alerts"
    private const val NOTIFICATION_ID = 7313

    fun show(context: Context, dbfs: Double) {
        val manager = context.getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= 26) {
            manager.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    "CURA sound alerts",
                    NotificationManager.IMPORTANCE_HIGH
                ).apply { description = "Alerts when a concerning loud sound is detected." }
            )
        }
        manager.notify(
            NOTIFICATION_ID,
            NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_alert)
                .setContentTitle("CURA detected a loud sound")
                .setContentText("Open CURA to complete a sound alert check-in. ${"%.0f".format(dbfs)} dBFS")
                .setContentIntent(openApp(context, NOTIFICATION_ID))
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .build()
        )
    }
}

private fun openApp(context: Context, requestCode: Int): PendingIntent? {
    val launchIntent = context.packageManager.getLaunchIntentForPackage(context.packageName)
        ?: return null
    launchIntent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
    val flags = PendingIntent.FLAG_UPDATE_CURRENT or
        if (Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0
    return PendingIntent.getActivity(context, requestCode, launchIntent, flags)
}

internal object CheckinScheduling {
    private const val PREFS = CuraAndroidPlugin.PREFS
    private const val WAKE = "checkin_wake_minute"
    private const val BED = "checkin_bed_minute"
    private const val FIRST_CHECKIN_DELAY_MILLIS = 60L * 60L * 1000L

    fun saveAndSchedule(context: Context, wake: Int, bed: Int) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putInt(WAKE, wake)
            .putInt(BED, bed)
            .apply()
        scheduleNext(context, FIRST_CHECKIN_DELAY_MILLIS)
    }

    fun cancel(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .remove(WAKE)
            .remove(BED)
            .apply()
        val alarmManager = context.getSystemService(AlarmManager::class.java)
        alarmManager.cancel(pendingIntent(context))
    }

    fun scheduleNext(context: Context, minimumDelayMillis: Long = 0L) {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val wake = prefs.getInt(WAKE, -1)
        val bed = prefs.getInt(BED, -1)
        if (wake !in 0..1439 || bed !in 0..1439 || wake == bed) return

        val now = Calendar.getInstance()
        val next = findNext(wake, bed, now, minimumDelayMillis) ?: return
        val alarmManager = context.getSystemService(AlarmManager::class.java)
        if (Build.VERSION.SDK_INT >= 23) {
            alarmManager.setAndAllowWhileIdle(
                AlarmManager.RTC_WAKEUP,
                next.timeInMillis,
                pendingIntent(context)
            )
        } else {
            alarmManager.set(AlarmManager.RTC_WAKEUP, next.timeInMillis, pendingIntent(context))
        }
    }

    fun isAwake(context: Context, now: Calendar): Boolean {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val wake = prefs.getInt(WAKE, -1)
        val bed = prefs.getInt(BED, -1)
        if (wake !in 0..1439 || bed !in 0..1439 || wake == bed) return false
        val minute = now.get(Calendar.HOUR_OF_DAY) * 60 + now.get(Calendar.MINUTE)
        return if (wake < bed) minute in wake..bed
        else minute >= wake || minute <= bed
    }

    private fun findNext(
        wake: Int,
        bed: Int,
        now: Calendar,
        minimumDelayMillis: Long
    ): Calendar? {
        val earliestTimeMillis = now.timeInMillis + minimumDelayMillis
        val today = now.clone() as Calendar
        today.set(Calendar.HOUR_OF_DAY, 0)
        today.set(Calendar.MINUTE, 0)
        today.set(Calendar.SECOND, 0)
        today.set(Calendar.MILLISECOND, 0)
        for (offset in 0..2) {
            val day = today.clone() as Calendar
            day.add(Calendar.DAY_OF_YEAR, offset)
            val candidate = day.clone() as Calendar
            candidate.set(Calendar.HOUR_OF_DAY, wake / 60)
            candidate.set(Calendar.MINUTE, wake % 60)
            val end = day.clone() as Calendar
            end.set(Calendar.HOUR_OF_DAY, bed / 60)
            end.set(Calendar.MINUTE, bed % 60)
            if (wake > bed) end.add(Calendar.DAY_OF_YEAR, 1)
            while (candidate.before(end) || candidate.timeInMillis == end.timeInMillis) {
                if (candidate.timeInMillis >= earliestTimeMillis) return candidate
                candidate.add(Calendar.HOUR_OF_DAY, 1)
            }
        }
        return null
    }

    private fun pendingIntent(context: Context): PendingIntent {
        val intent = Intent(context, CheckinAlarmReceiver::class.java)
            .setAction("com.cura.android.HOURLY_CHECKIN")
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or
            if (Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0
        return PendingIntent.getBroadcast(context, 7312, intent, flags)
    }
}
