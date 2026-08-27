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
  QualityPlantResult? _plantResult;
  bool _validating = false;
  bool _identifyingPlant = false;

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
      _plantResult = null;
      _validating = true;
      _identifyingPlant = false;
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
        _validating = false;
      });

      if (_validationResult?.valid == true) {
        await _identifyPlant(image, imageBytes);
      }
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

  Future<void> _identifyPlant(XFile image, Uint8List imageBytes) async {
    if (!mounted) {
      return;
    }

    setState(() {
      _plantResult = null;
      _identifyingPlant = true;
    });

    try {
      final uri = Uri.parse('${_apiBaseUrl()}/api/quality/identify-plant');
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

      final response = await request.send().timeout(const Duration(seconds: 30));
      final responseBody = await response.stream.bytesToString();
      final data = jsonDecode(responseBody) as Map<String, dynamic>;

      if (!mounted) {
        return;
      }

      setState(() {
        _plantResult = QualityPlantResult.fromJson(data);
      });
    } on TimeoutException {
      _showPlantError('Plant identification timed out. Please try again.');
    } on http.ClientException {
      _showPlantError('Could not reach the plant identification service.');
    } catch (_) {
      _showPlantError('Could not identify this plant image.');
    } finally {
      if (mounted) {
        setState(() => _identifyingPlant = false);
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
      _plantResult = null;
      _identifyingPlant = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  void _showPlantError(String message) {
    if (!mounted) {
      return;
    }

    setState(() {
      _plantResult = QualityPlantResult.failure(reason: 'MODEL_NOT_AVAILABLE');
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
            const SizedBox(height: 18),
            _PlantIdentificationPanel(
              result: _plantResult,
              identifying: _identifyingPlant,
              enabled: _validationResult?.valid == true,
            ),
          ],
        ),
      ),
    );
  }
}

class _PlantIdentificationPanel extends StatelessWidget {
  const _PlantIdentificationPanel({
    required this.result,
    required this.identifying,
    required this.enabled,
  });

  final QualityPlantResult? result;
  final bool identifying;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    if (identifying) {
      return const _StatusPanel(
        icon: SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(strokeWidth: 2.4),
        ),
        title: 'Identifying plant',
        subtitle: 'Preparing a 224 x 224 letterbox image for species prediction.',
      );
    }

    if (!enabled) {
      return const _StatusPanel(
        icon: Icon(Icons.eco_outlined, color: AppColors.muted),
        title: 'Plant identification waiting',
        subtitle: 'A valid image is required before species prediction.',
      );
    }

    if (result == null) {
      return const _StatusPanel(
        icon: Icon(Icons.eco_outlined, color: AppColors.muted),
        title: 'Plant identification ready',
        subtitle: 'Species prediction starts after validation passes.',
      );
    }

    final title = result!.accepted
        ? '${result!.species} detected'
        : _plantReasonTitle(result!.reason);
    final subtitle = result!.accepted
        ? _acceptedSubtitle(result!)
        : _plantReasonHelp(result!.reason, result!);

    return _StatusPanel(
      icon: Icon(
        result!.accepted
            ? Icons.check_circle_outline_rounded
            : Icons.info_outline_rounded,
        color: result!.accepted ? AppColors.primary : AppColors.danger,
      ),
      title: title,
      subtitle: subtitle,
      plantResult: result,
    );
  }

  String _acceptedSubtitle(QualityPlantResult result) {
    final scientificName = result.scientificName;
    if (scientificName == null || scientificName.isEmpty) {
      return 'Accepted for the next model stage.';
    }

    return '$scientificName. Accepted for the next model stage.';
  }

  String _plantReasonTitle(String? reason) {
    switch (reason) {
      case 'UNKNOWN_PLANT':
        return 'Unsupported plant species';
      case 'LOW_SPECIES_CONFIDENCE':
        return 'Low species confidence';
      case 'INVALID_IMAGE':
        return 'Image could not be identified';
      case 'MODEL_NOT_AVAILABLE':
        return 'Plant model is unavailable';
      case 'MODEL_RUNTIME_MISSING':
        return 'Plant model runtime is missing';
      default:
        return 'Plant identification stopped';
    }
  }

  String _plantReasonHelp(String? reason, QualityPlantResult result) {
    switch (reason) {
      case 'UNKNOWN_PLANT':
        return 'The model selected Unknown, so the pipeline should stop here.';
      case 'LOW_SPECIES_CONFIDENCE':
        return 'Confidence was ${result.confidencePercent}; retake a clearer leaf image.';
      case 'INVALID_IMAGE':
        return 'Choose a valid leaf image and try again.';
      case 'MODEL_NOT_AVAILABLE':
        return 'Train or configure the EfficientNetV2-B0 model before real use.';
      case 'MODEL_RUNTIME_MISSING':
        return 'Install TensorFlow in the backend environment before real model inference.';
      default:
        return 'Please try another image.';
    }
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
    this.plantResult,
  });

  final Widget icon;
  final String title;
  final String subtitle;
  final QualityValidationResult? result;
  final QualityPlantResult? plantResult;

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
          if (plantResult != null) ...[
            const SizedBox(height: 14),
            _PlantResultDetails(result: plantResult!),
          ],
        ],
      ),
    );
  }
}

class _PlantResultDetails extends StatelessWidget {
  const _PlantResultDetails({required this.result});

  final QualityPlantResult result;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            _MetricChip(label: 'Species', value: result.species),
            _MetricChip(label: 'Confidence', value: result.confidencePercent),
            _MetricChip(label: 'Model', value: result.model ?? 'Configured model'),
          ],
        ),
        if (result.mode == 'mock') ...[
          const SizedBox(height: 10),
          const Text(
            'Mock prediction active until a trained model file is configured.',
            style: TextStyle(
              color: AppColors.muted,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ],
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

class QualityPlantResult {
  const QualityPlantResult({
    required this.species,
    required this.confidence,
    required this.accepted,
    this.scientificName,
    this.reason,
    this.model,
    this.mode,
  });

  factory QualityPlantResult.failure({required String reason}) {
    return QualityPlantResult(
      species: 'Unknown',
      confidence: 0,
      accepted: false,
      reason: reason,
    );
  }

  factory QualityPlantResult.fromJson(Map<String, dynamic> json) {
    return QualityPlantResult(
      species: (json['species'] as String?) ?? 'Unknown',
      scientificName: json['scientific_name'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      accepted: json['accepted'] == true,
      reason: json['reason'] as String?,
      model: json['model'] as String?,
      mode: json['mode'] as String?,
    );
  }

  final String species;
  final String? scientificName;
  final double confidence;
  final bool accepted;
  final String? reason;
  final String? model;
  final String? mode;

  String get confidencePercent => '${(confidence * 100).toStringAsFixed(1)}%';
}
