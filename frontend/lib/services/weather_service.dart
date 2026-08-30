import 'dart:convert';

import 'package:geocoding/geocoding.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;

class WeatherData {
  const WeatherData({
    required this.temperature,
    required this.humidity,
    required this.rainfall,
    this.location,
  });

  final double temperature;
  final double humidity;
  final double rainfall;
  final String? location;
}

class WeatherException implements Exception {
  const WeatherException(this.message);

  final String message;
}

class WeatherService {
  Future<WeatherData> autoDetectWeather() async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      throw const WeatherException('Location services are disabled.');
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      throw const WeatherException(
        'Location permission is required to detect weather.',
      );
    }

    final position = await Geolocator.getCurrentPosition();
    final uri = Uri.https('api.open-meteo.com', '/v1/forecast', {
      'latitude': position.latitude.toString(),
      'longitude': position.longitude.toString(),
      'current': 'temperature_2m,relative_humidity_2m,precipitation',
    });
    final response = await http.get(uri).timeout(const Duration(seconds: 10));
    if (response.statusCode != 200) {
      throw const WeatherException('Failed to fetch weather data.');
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    final current = body['current'] as Map<String, dynamic>;
    String? location;
    try {
      final placemarks = await placemarkFromCoordinates(
        position.latitude,
        position.longitude,
      );
      if (placemarks.isNotEmpty) location = placemarks.first.locality;
    } catch (_) {
      location = null;
    }

    return WeatherData(
      temperature: (current['temperature_2m'] as num).toDouble(),
      humidity: (current['relative_humidity_2m'] as num).toDouble(),
      rainfall: (current['precipitation'] as num).toDouble(),
      location: location,
    );
  }
}
