import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/services/api_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:image_picker/image_picker.dart';

void main() {
  test(
    'soil image upload sends picked image bytes as multipart data',
    () async {
      const imageBytes = [115, 111, 105, 108, 45, 105, 109, 97, 103, 101];
      final client = MockClient((request) async {
        expect(request.url.path, '/api/predict-soil');
        expect(
          request.headers['content-type'],
          startsWith('multipart/form-data;'),
        );

        final body = String.fromCharCodes(request.bodyBytes);
        expect(body, contains('name="image"'));
        expect(body, contains('filename="soil-photo.jpg"'));
        expect(body, contains('soil-image'));

        return http.Response(
          jsonEncode({
            'success': true,
            'available': true,
            'model_available': true,
            'soil_type': 'Alluvial soil',
            'confidence': 0.9,
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });
      final service = ApiService(client: client);

      final result = await service.predictSoil(
        XFile.fromData(Uint8List.fromList(imageBytes), path: 'soil-photo.jpg'),
      );

      expect(result['soil_type'], 'Alluvial soil');
    },
  );

  test(
    'soil upload reports unsupported image response from the backend',
    () async {
      final client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'success': false,
            'available': true,
            'model_available': true,
            'message':
                'This image could not be matched to a supported soil type.',
            'soil_type': null,
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });
      final service = ApiService(client: client);

      await expectLater(
        service.predictSoil(
          XFile.fromData(Uint8List.fromList([1, 2, 3]), path: 'flower.jpg'),
        ),
        throwsA(
          isA<ApiException>().having(
            (error) => error.message,
            'message',
            contains('supported soil type'),
          ),
        ),
      );
    },
  );
}
