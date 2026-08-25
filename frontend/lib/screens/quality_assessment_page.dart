import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import '../theme/app_colors.dart';

class QualityAssessmentPage extends StatefulWidget {
  const QualityAssessmentPage({super.key});

  @override
  State<QualityAssessmentPage> createState() => _QualityAssessmentPageState();
}

class _QualityAssessmentPageState extends State<QualityAssessmentPage> {
  final ImagePicker _picker = ImagePicker();
  Uint8List? _selectedImageBytes;
  QualityValidationResult? _validationResult;
  bool _validating = false;

  Future<void> _pickImage(ImageSource source) async {
    final image = await _picker.pickImage(
      source: source,
      imageQuality: 95,
      preferredCameraDevice: CameraDevice.rear,
    );

    if (image == null) {
      return;
    }

    final imageBytes = await image.readAsBytes();

    setState(() {
      _selectedImageBytes = imageBytes;
      _validationResult = null;
      _validating = true;
    });

    await _validateImage(image, imageBytes);
  }

  Future<void> _validateImage(XFile image, Uint8List imageBytes) async {
    try {
      final uri = Uri.parse('${_apiBaseUrl()}/api/quality/validate-image');
      final request = http.MultipartRequest('POST', uri)
        ..files.add(
          http.MultipartFile.fromBytes(
            'image',
            imageBytes,
            filename: image.name.isEmpty
                ? 'quality.leaf-image.jpg'
                : image.name,
          ),
        );

      final response = await request.send().timeout(const Duration(seconds: 25));
      final responseBody = await response.stream.bytesToString();
      final data = jsonDecode(responseBody) as Map<String, dynamic>;

      if (!mounted) {
        return;
      }

      setState(() {
        _validationResult = QualityValidationResult.fromJson(data);
      });
    } on TimeoutException {
      _showValidationError('Image validation timed out. Please try again.');
    } on http.ClientException {
      _showValidationError('Could not reach the validation service.');
    } catch (_) {
      _showValidationError('Could not validate this image.');
    } finally {
      if (mounted) {
        setState(() => _validating = false);
      }
    }
  }

  void _showValidationError(String message) {
    if (!mounted) {
      return;
    }

    setState(() {
      _validationResult = QualityValidationResult.failure(
        reason: 'INVALID_IMAGE',
      );
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  String _apiBaseUrl() {
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:5000';
    }

    return 'http://127.0.0.1:5000';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Assess Quality'), centerTitle: false),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
          children: [
            const _QualityHeader(),
            const SizedBox(height: 22),
            _ImagePickerPanel(
              selectedImageBytes: _selectedImageBytes,
              validating: _validating,
              onCameraPressed: () => _pickImage(ImageSource.camera),
              onGalleryPressed: () => _pickImage(ImageSource.gallery),
            ),
            const SizedBox(height: 18),
            _ValidationPanel(
              result: _validationResult,
              validating: _validating,
            ),
          ],
        ),
      ),
    );
  }
}

class _QualityHeader extends StatelessWidget {
  const _QualityHeader();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: const Color(0xFFFFF1D2),
            borderRadius: BorderRadius.circular(14),
          ),
          child: const Icon(
            Icons.camera_enhance_rounded,
            color: Color(0xFFE99A1E),
            size: 26,
          ),
        ),
        const SizedBox(width: 14),
        const Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Leaf Image Check',
                style: TextStyle(
                  color: AppColors.text,
                  fontSize: 22,
                  fontWeight: FontWeight.w900,
                ),
              ),
              SizedBox(height: 4),
              Text(
                'Upload a clear plant leaf image before AI assessment.',
                style: TextStyle(
                  color: AppColors.muted,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ImagePickerPanel extends StatelessWidget {
  const _ImagePickerPanel({
    required this.selectedImageBytes,
    required this.validating,
    required this.onCameraPressed,
    required this.onGalleryPressed,
  });

  final Uint8List? selectedImageBytes;
  final bool validating;
  final VoidCallback onCameraPressed;
  final VoidCallback onGalleryPressed;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(18),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        children: [
          AspectRatio(
            aspectRatio: 4 / 3,
            child: Container(
              width: double.infinity,
              clipBehavior: Clip.antiAlias,
              decoration: BoxDecoration(
                color: const Color(0xFFF7F9F7),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.border),
              ),
              child: selectedImageBytes == null
                  ? const _EmptyImageState()
                  : Image.memory(
                      selectedImageBytes!,
                      fit: BoxFit.cover,
                    ),
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _PickerButton(
                  label: 'Camera',
                  icon: Icons.photo_camera_rounded,
                  onPressed: validating ? null : onCameraPressed,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _PickerButton(
                  label: 'Device',
                  icon: Icons.photo_library_rounded,
                  onPressed: validating ? null : onGalleryPressed,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _EmptyImageState extends StatelessWidget {
  const _EmptyImageState();

  @override
  Widget build(BuildContext context) {
    return const Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(
          Icons.add_photo_alternate_outlined,
          color: AppColors.muted,
          size: 44,
        ),
        SizedBox(height: 10),
        Text(
          'No leaf image selected',
          style: TextStyle(
            color: AppColors.text,
            fontSize: 16,
            fontWeight: FontWeight.w900,
          ),
        ),
        SizedBox(height: 4),
        Text(
          'Take a photo or choose one from your device.',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: AppColors.muted,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

class _PickerButton extends StatelessWidget {
  const _PickerButton({
    required this.label,
    required this.icon,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return FilledButton.icon(
      onPressed: onPressed,
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(48),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
      icon: Icon(icon, size: 20),
      label: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(fontWeight: FontWeight.w900),
      ),
    );
  }
}

class _ValidationPanel extends StatelessWidget {
  const _ValidationPanel({
    required this.result,
    required this.validating,
  });

  final QualityValidationResult? result;
  final bool validating;

  @override
  Widget build(BuildContext context) {
    if (validating) {
      return const _StatusPanel(
        icon: SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(strokeWidth: 2.4),
        ),
        title: 'Validating image',
        subtitle: 'Checking resolution, blur, darkness, and exposure.',
      );
    }

    if (result == null) {
      return const _StatusPanel(
        icon: Icon(Icons.fact_check_outlined, color: AppColors.muted),
        title: 'Input validation pending',
        subtitle: 'The next AI steps unlock after the image passes validation.',
      );
    }

    if (!result!.valid) {
      return _StatusPanel(
        icon: const Icon(Icons.error_outline_rounded, color: AppColors.danger),
        title: _reasonTitle(result!.reason),
        subtitle: _reasonHelp(result!.reason),
        result: result,
      );
    }

    return _StatusPanel(
      icon: const Icon(
        Icons.check_circle_outline_rounded,
        color: AppColors.primary,
      ),
      title: 'Image passed validation',
      subtitle: 'Ready for plant identification and visual quality assessment.',
      result: result,
    );
  }

  String _reasonTitle(String? reason) {
    switch (reason) {
      case 'LOW_RESOLUTION':
        return 'Image resolution is too low';
      case 'IMAGE_TOO_BLURRY':
        return 'Image is too blurry';
      case 'IMAGE_TOO_DARK':
        return 'Image is too dark';
      case 'IMAGE_OVEREXPOSED':
        return 'Image is overexposed';
      default:
        return 'Image could not be validated';
    }
  }

  String _reasonHelp(String? reason) {
    switch (reason) {
      case 'LOW_RESOLUTION':
        return 'Use a larger image so leaf details are visible.';
      case 'IMAGE_TOO_BLURRY':
        return 'Retake the photo with steady focus and good distance.';
      case 'IMAGE_TOO_DARK':
        return 'Move the leaf into brighter, even lighting.';
      case 'IMAGE_OVEREXPOSED':
        return 'Avoid harsh light or flash glare on the leaf surface.';
      default:
        return 'Choose a valid image file and try again.';
    }
  }
}

class _StatusPanel extends StatelessWidget {
  const _StatusPanel({
    required this.icon,
    required this.title,
    required this.subtitle,
    this.result,
  });

  final Widget icon;
  final String title;
  final String subtitle;
  final QualityValidationResult? result;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF9FAF7),
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(width: 28, height: 28, child: Center(child: icon)),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        color: AppColors.text,
                        fontSize: 16,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: const TextStyle(
                        color: AppColors.muted,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (result != null && result!.hasMetrics) ...[
            const SizedBox(height: 14),
            _MetricGrid(result: result!),
          ],
        ],
      ),
    );
  }
}

class _MetricGrid extends StatelessWidget {
  const _MetricGrid({required this.result});

  final QualityValidationResult result;

  @override
  Widget build(BuildContext context) {
    final resolution = result.resolution;

    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        if (resolution != null)
          _MetricChip(
            label: 'Resolution',
            value: '${resolution.width} x ${resolution.height}',
          ),
        if (result.blurScore != null)
          _MetricChip(
            label: 'Blur score',
            value: result.blurScore!.toStringAsFixed(2),
          ),
        if (result.brightness != null)
          _MetricChip(
            label: 'Brightness',
            value: result.brightness!.toStringAsFixed(2),
          ),
      ],
    );
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 132,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: AppColors.muted,
              fontSize: 12,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: AppColors.text,
              fontSize: 15,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class QualityValidationResult {
  const QualityValidationResult({
    required this.valid,
    this.reason,
    this.resolution,
    this.blurScore,
    this.brightness,
  });

  factory QualityValidationResult.failure({required String reason}) {
    return QualityValidationResult(valid: false, reason: reason);
  }

  factory QualityValidationResult.fromJson(Map<String, dynamic> json) {
    final resolutionJson = json['resolution'] as Map<String, dynamic>?;

    return QualityValidationResult(
      valid: json['valid'] == true,
      reason: json['reason'] as String?,
      resolution: resolutionJson == null
          ? null
          : QualityImageResolution.fromJson(resolutionJson),
      blurScore: (json['blur_score'] as num?)?.toDouble(),
      brightness: (json['brightness'] as num?)?.toDouble(),
    );
  }

  final bool valid;
  final String? reason;
  final QualityImageResolution? resolution;
  final double? blurScore;
  final double? brightness;

  bool get hasMetrics =>
      resolution != null || blurScore != null || brightness != null;
}

class QualityImageResolution {
  const QualityImageResolution({
    required this.width,
    required this.height,
  });

  factory QualityImageResolution.fromJson(Map<String, dynamic> json) {
    return QualityImageResolution(
      width: (json['width'] as num?)?.toInt() ?? 0,
      height: (json['height'] as num?)?.toInt() ?? 0,
    );
  }

  final int width;
  final int height;
}
