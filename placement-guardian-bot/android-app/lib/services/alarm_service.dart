import 'dart:async';
import 'package:flutter/services.dart';
import 'package:audioplayers/audioplayers.dart';

class AlarmService {
  final AudioPlayer _audioPlayer = AudioPlayer();
  Timer? _alarmTimer;
  bool _isAlarmPlaying = false;
  
  static const MethodChannel _channel = MethodChannel('placement_guardian/alarm');
  
  Future<void> triggerAlarm() async {
    if (_isAlarmPlaying) {
      return;
    }
    
    _isAlarmPlaying = true;
    
    await _setMaxVolume();
    await _wakeScreen();
    
    await _playAlarmSound();
    
    _startAlarmLoop();
  }
  
  Future<void> _setMaxVolume() async {
    try {
      await _channel.invokeMethod('setMaxVolume');
    } catch (e) {
      print('AlarmService: Could not set max volume: $e');
    }
  }
  
  Future<void> _wakeScreen() async {
    try {
      await _channel.invokeMethod('wakeScreen');
    } catch (e) {
      print('AlarmService: Could not wake screen: $e');
    }
  }
  
  Future<void> _playAlarmSound() async {
    try {
      await _audioPlayer.setReleaseMode(ReleaseMode.loop);
      await _audioPlayer.setVolume(1.0);
      
      await _audioPlayer.play(
        AssetSource('sounds/alarm.mp3'),
        mode: PlayerMode.lowLatency,
      );
    } catch (e) {
      print('AlarmService: Error playing alarm: $e');
    }
  }
  
  void _startAlarmLoop() {
    _alarmTimer?.cancel();
    _alarmTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
      if (_isAlarmPlaying) {
        _vibrate();
      }
    });
  }
  
  Future<void> _vibrate() async {
    try {
      await HapticFeedback.vibrate();
      await HapticFeedback.vibrate();
      await HapticFeedback.vibrate();
    } catch (e) {
      print('AlarmService: Vibration error: $e');
    }
  }
  
  Future<void> stopAlarm() async {
    _isAlarmPlaying = false;
    _alarmTimer?.cancel();
    _alarmTimer = null;
    
    await _audioPlayer.stop();
  }
  
  Future<void> testAlarm() async {
    await triggerAlarm();
    
    Future.delayed(const Duration(seconds: 5), () {
      stopAlarm();
    });
  }
}
