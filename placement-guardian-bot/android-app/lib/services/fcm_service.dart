import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import '../services/alarm_service.dart';

class FCMService {
  final FirebaseMessaging _firebaseMessaging = FirebaseMessaging.instance;
  final AlarmService _alarmService = AlarmService();
  
  static const String _alarmChannelId = 'placement_alarm';
  static const String _alarmChannelName = 'Placement Alerts';
  static const String _alarmChannelDesc = 'Critical placement email alerts with forced alarm';
  
  Future<void> initialize() async {
    await _createNotificationChannel();
    
    NotificationSettings settings = await _firebaseMessaging.requestPermission(
      alert: true,
      announcement: false,
      badge: true,
      carPlay: false,
      criticalAlert: true,
      provisional: false,
      sound: true,
    );
    
    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      print('FCM: Permission granted');
    }
    
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);
    FirebaseMessaging.onMessageOpenedApp.listen(_handleMessageOpenedApp);
    
    String? token = await _firebaseMessaging.getToken();
    print('FCM Token: $token');
  }
  
  Future<void> _createNotificationChannel() async {
    final androidPlugin = FlutterLocalNotificationsPlugin();
    
    const AndroidNotificationChannel alarmChannel = AndroidNotificationChannel(
      _alarmChannelId,
      _alarmChannelName,
      description: _alarmChannelDesc,
      importance: Importance.max,
      playSound: true,
      enableVibration: true,
      enableLights: true,
      ledColor: Color(0xFFFF0000),
      ledOnMs: 1000,
      ledOffMs: 500,
    );
    
    await androidPlugin
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(alarmChannel);
  }
  
  void _handleForegroundMessage(RemoteMessage message) {
    print('FCM: Foreground message received');
    
    if (message.data['type'] == 'placement_alarm') {
      _showAlarmNotification(
        title: message.notification?.title ?? 'PLACEMENT ALERT',
        body: message.notification?.body ?? 'Check your placement email!',
        data: message.data,
      );
      _alarmService.triggerAlarm();
    }
  }
  
  void _handleMessageOpenedApp(RemoteMessage message) {
    print('FCM: App opened from notification');
    
    if (message.data['type'] == 'placement_alarm') {
      _alarmService.triggerAlarm();
    }
  }
  
  Future<void> _showAlarmNotification({
    required String title,
    required String body,
    required Map<String, dynamic> data,
  }) async {
    final androidPlugin = FlutterLocalNotificationsPlugin();
    
    const AndroidNotificationDetails androidDetails = AndroidNotificationDetails(
      _alarmChannelId,
      _alarmChannelName,
      channelDescription: _alarmChannelDesc,
      importance: Importance.max,
      priority: Priority.max,
      playSound: true,
      enableVibration: true,
      enableLights: true,
      fullScreenIntent: true,
      category: AndroidNotificationCategory.alarm,
      visibility: NotificationVisibility.public,
    );
    
    const NotificationDetails details = NotificationDetails(android: androidDetails);
    
    await androidPlugin.show(0, title, body, details, payload: 'placement_alarm');
  }
  
  Future<void> sendTokenToServer(String token) async {
    // TODO: Send FCM token to backend for targeting this device
  }
}

class Color {
  final int value;
  const Color(this.value);
}
