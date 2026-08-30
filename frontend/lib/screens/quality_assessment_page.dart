import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import '../theme/app_colors.dart';
import 'chat/general_public_chat_page.dart';

class QualityAssessmentPage extends StatefulWidget {
  const QualityAssessmentPage({super.key});

  @override
  State<QualityAssessmentPage> createState() => _QualityAssessmentPageState();
}

class _QualityAssessmentPageState extends State<QualityAssessmentPage> {
  static const int _maxImages = 3;
  final ImagePicker _picker = ImagePicker();
  final List<QualitySelectedImage> _selectedImages = [];
  QualityManualInputs _manualInputs = const QualityManualInputs();
  QualityValidationResult? _validationResult;
  QualityPlantResult? _plantResult;
  QualityConditionResult? _conditionResult;
  bool _validating = false;
  bool _identifyingPlant = false;
  bool _assessingCondition = false;

  Future<void> _pickImage(ImageSource source) async {
    final image = await _picker.pickImage(
      source: source,
      imageQuality: 95,
      preferredCameraDevice: CameraDevice.rear,
    );

    if (image == null) {
      return;
    }

    await _addImages([image]);
  }

  Future<void> _pickDeviceImages() async {
    final remainingSlots = _maxImages - _selectedImages.length;
    if (remainingSlots <= 0) {
      _showMessage('You can add up to 3 images.');
      return;
    }

    final images = await _picker.pickMultiImage(
      imageQuality: 95,
      limit: remainingSlots,
    );

    if (images.isEmpty) {
      return;
    }

    await _addImages(images.take(remainingSlots).toList());
  }

  Future<void> _addImages(List<XFile> images) async {
    final selectedImages = <QualitySelectedImage>[];

    for (final image in images) {
      selectedImages.add(
        QualitySelectedImage(
          file: image,
          bytes: await image.readAsBytes(),
        ),
      );
    }

    setState(() {
      _selectedImages.addAll(selectedImages);
      _validationResult = null;
      _plantResult = null;
      _conditionResult = null;
      _validating = true;
      _identifyingPlant = false;
      _assessingCondition = false;
    });

    await _validateImages();
  }

  Future<void> _validateImages() async {
    try {
      final validationResults = <QualityValidationResult>[];

      for (final image in _selectedImages) {
        final data = await _postSingleImage(
          endpoint: '/api/quality/validate-image',
          image: image,
          timeout: const Duration(seconds: 25),
        );
        validationResults.add(QualityValidationResult.fromJson(data));
      }

      if (!mounted) {
        return;
      }

      QualityValidationResult? failedResult;
      for (final result in validationResults) {
        if (!result.valid) {
          failedResult = result;
          break;
        }
      }
      final validationResult = failedResult ??
          QualityValidationResult.combinedSuccess(validationResults);

      setState(() {
        _validationResult = validationResult;
        _validating = false;
      });

      if (validationResult.valid) {
        await _identifyPlant();
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

  Future<void> _identifyPlant() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _plantResult = null;
      _identifyingPlant = true;
    });

    try {
      final uri = Uri.parse(
        '${_apiBaseUrl()}/api/quality/identify-plant-multiple',
      );
      final request = http.MultipartRequest('POST', uri)
        ..files.addAll(
          _selectedImages.map((image) => http.MultipartFile.fromBytes(
            'image',
            image.bytes,
            filename: image.file.name.isEmpty
                ? 'quality.leaf-image.jpg'
                : image.file.name,
          )),
        );
      if (_manualInputs.hasValues) {
        request.fields['manual_inputs'] = jsonEncode(_manualInputs.toJson());
      }

      final response = await request.send().timeout(const Duration(seconds: 30));
      final responseBody = await response.stream.bytesToString();
      final data = jsonDecode(responseBody) as Map<String, dynamic>;

      if (!mounted) {
        return;
      }

      setState(() {
        _plantResult = QualityPlantResult.fromJson(data);
      });

      if (_plantResult?.accepted == true) {
        await _assessCondition();
      }
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

  Future<void> _assessCondition() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _conditionResult = null;
      _assessingCondition = true;
    });

    try {
      final uri = Uri.parse('${_apiBaseUrl()}/api/quality/assess-condition');
      final request = http.MultipartRequest('POST', uri)
        ..files.addAll(
          _selectedImages.map((image) => http.MultipartFile.fromBytes(
            'image',
            image.bytes,
            filename: image.file.name.isEmpty
                ? 'quality.leaf-image.jpg'
                : image.file.name,
          )),
        );
      if (_manualInputs.hasValues) {
        request.fields['manual_inputs'] = jsonEncode(_manualInputs.toJson());
      }

      final response = await request.send().timeout(const Duration(seconds: 35));
      final responseBody = await response.stream.bytesToString();
      final data = jsonDecode(responseBody) as Map<String, dynamic>;

      if (!mounted) {
        return;
      }

      setState(() {
        _conditionResult = QualityConditionResult.fromJson(data);
      });
    } on TimeoutException {
      _showConditionError('Condition assessment timed out. Please try again.');
    } on http.ClientException {
      _showConditionError('Could not reach the condition assessment service.');
    } catch (_) {
      _showConditionError('Could not assess this leaf condition.');
    } finally {
      if (mounted) {
        setState(() => _assessingCondition = false);
      }
    }
  }

  Future<Map<String, dynamic>> _postSingleImage({
    required String endpoint,
    required QualitySelectedImage image,
    required Duration timeout,
  }) async {
    final uri = Uri.parse('${_apiBaseUrl()}$endpoint');
    final request = http.MultipartRequest('POST', uri)
      ..files.add(
        http.MultipartFile.fromBytes(
          'image',
          image.bytes,
          filename: image.file.name.isEmpty
              ? 'quality.leaf-image.jpg'
              : image.file.name,
        ),
      );

    final response = await request.send().timeout(timeout);
    final responseBody = await response.stream.bytesToString();
    return jsonDecode(responseBody) as Map<String, dynamic>;
  }

  void _removeImage(int index) {
    if (index < 0 || index >= _selectedImages.length) {
      return;
    }

    setState(() {
      _selectedImages.removeAt(index);
      _validationResult = null;
      _plantResult = null;
      _conditionResult = null;
      _validating = _selectedImages.isNotEmpty;
      _identifyingPlant = false;
      _assessingCondition = false;
    });

    if (_selectedImages.isNotEmpty) {
      _validateImages();
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
      _conditionResult = null;
      _assessingCondition = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  void _showMessage(String message) {
    if (!mounted) {
      return;
    }

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
      _conditionResult = null;
      _assessingCondition = false;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  void _showConditionError(String message) {
    if (!mounted) {
      return;
    }

    setState(() {
      _conditionResult = QualityConditionResult.failure(
        reason: 'MODEL_NOT_AVAILABLE',
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
              selectedImages: _selectedImages,
              busy: _validating || _identifyingPlant || _assessingCondition,
              maxImages: _maxImages,
              onCameraPressed: () => _pickImage(ImageSource.camera),
              onGalleryPressed: _pickDeviceImages,
              onRemoveImage: _removeImage,
            ),
            if (_validationResult?.valid == false) ...[
              const SizedBox(height: 18),
              _ValidationPanel(
                result: _validationResult,
              ),
            ],
            if (_identifyingPlant || _plantResult?.accepted == false) ...[
              const SizedBox(height: 18),
              _PlantIdentificationPanel(
                result: _plantResult,
                identifying: _identifyingPlant,
                enabled: _validationResult?.valid == true,
              ),
            ],
            const SizedBox(height: 18),
            _ConditionAssessmentPanel(
              result: _conditionResult,
              plantResult: _plantResult,
              assessing: _assessingCondition,
              enabled: _plantResult?.accepted == true,
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
        if ((result.imageCount ?? 1) < 3) {
          return 'Confidence was ${result.confidencePercent}; add another view of the same plant.';
        }

        return 'Confidence was ${result.confidencePercent}; expert verification is recommended.';
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

class _ConditionAssessmentPanel extends StatelessWidget {
  const _ConditionAssessmentPanel({
    required this.result,
    required this.plantResult,
    required this.assessing,
    required this.enabled,
  });

  final QualityConditionResult? result;
  final QualityPlantResult? plantResult;
  final bool assessing;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    final acceptedPlant = plantResult?.accepted == true ? plantResult : null;

    return _buildStatusPanel(plantResult: acceptedPlant);
  }

  Widget _buildStatusPanel({QualityPlantResult? plantResult}) {
    final plantName = plantResult?.species;

    if (assessing) {
      return _StatusPanel(
        heading: plantName,
        icon: const SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(strokeWidth: 2.4),
        ),
        title: 'Assessing leaf condition',
        subtitle: 'Using the identified plant to select the condition head.',
      );
    }

    if (!enabled) {
      return const _StatusPanel(
        icon: Icon(Icons.health_and_safety_outlined, color: AppColors.muted),
        title: 'Condition assessment waiting',
        subtitle: 'An accepted plant prediction is required before this step.',
      );
    }

    if (result == null) {
      return _StatusPanel(
        heading: plantName,
        icon: const Icon(
          Icons.health_and_safety_outlined,
          color: AppColors.muted,
        ),
        title: 'Condition assessment ready',
        subtitle: 'The disease model runs after plant identification is accepted.',
      );
    }

    final condition = result!.condition;
    if (condition == null) {
      return _StatusPanel(
        heading: plantName,
        icon: const Icon(Icons.info_outline_rounded, color: AppColors.danger),
        title: _reasonTitle(result!.reason),
        subtitle: _reasonHelp(result!.reason),
      );
    }

    final isHealthy = condition.status == 'healthy';
    return _StatusPanel(
      heading: plantName,
      icon: Icon(
        isHealthy
            ? Icons.check_circle_outline_rounded
            : Icons.warning_amber_rounded,
        color: isHealthy ? AppColors.primary : AppColors.danger,
      ),
      title: isHealthy
          ? 'Leaf appears healthy'
          : '${condition.displayName} detected',
      subtitle: isHealthy
          ? 'Continuing to maturity-stage assessment when supported.'
          : null,
      plantResult: plantResult,
      conditionResult: result,
    );
  }

  String _reasonTitle(String? reason) {
    switch (reason) {
      case 'UNSUPPORTED_CONDITION_HEAD':
        return 'No condition head for this plant';
      case 'LOW_CONDITION_CONFIDENCE':
        return 'Low condition confidence';
      case 'MODEL_RUNTIME_MISSING':
        return 'Condition model runtime is missing';
      default:
        return 'Condition assessment unavailable';
    }
  }

  String _reasonHelp(String? reason) {
    switch (reason) {
      case 'UNSUPPORTED_CONDITION_HEAD':
        return 'Add this species to the condition model config before disease assessment.';
      case 'LOW_CONDITION_CONFIDENCE':
        return 'Expert verification recommended.';
      case 'MODEL_RUNTIME_MISSING':
        return 'Install TensorFlow in the backend environment before real model inference.';
      default:
        return 'Train or configure the condition model before real use.';
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
    required this.selectedImages,
    required this.busy,
    required this.maxImages,
    required this.onCameraPressed,
    required this.onGalleryPressed,
    required this.onRemoveImage,
  });

  final List<QualitySelectedImage> selectedImages;
  final bool busy;
  final int maxImages;
  final VoidCallback onCameraPressed;
  final VoidCallback onGalleryPressed;
  final ValueChanged<int> onRemoveImage;

  @override
  Widget build(BuildContext context) {
    final hasImages = selectedImages.isNotEmpty;

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
              child: !hasImages
                  ? const _EmptyImageState()
                  : Image.memory(
                      selectedImages.last.bytes,
                      fit: BoxFit.contain,
                    ),
            ),
          ),
          if (hasImages) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    '${selectedImages.length} of $maxImages images selected',
                    style: const TextStyle(
                      color: AppColors.muted,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                if (selectedImages.length < maxImages)
                  const Text(
                    'Add another view',
                    style: TextStyle(
                      color: AppColors.primary,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            _SelectedImageStrip(
              selectedImages: selectedImages,
              onRemoveImage: busy ? null : onRemoveImage,
            ),
          ],
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: _PickerButton(
                  label: 'Camera',
                  icon: Icons.photo_camera_rounded,
                  onPressed: busy || selectedImages.length >= maxImages
                      ? null
                      : onCameraPressed,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _PickerButton(
                  label: 'Device',
                  icon: Icons.photo_library_rounded,
                  onPressed: busy || selectedImages.length >= maxImages
                      ? null
                      : onGalleryPressed,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SelectedImageStrip extends StatelessWidget {
  const _SelectedImageStrip({
    required this.selectedImages,
    required this.onRemoveImage,
  });

  final List<QualitySelectedImage> selectedImages;
  final ValueChanged<int>? onRemoveImage;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 72,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: selectedImages.length,
        separatorBuilder: (_, _) => const SizedBox(width: 10),
        itemBuilder: (context, index) {
          return Stack(
            clipBehavior: Clip.none,
            children: [
              Container(
                width: 72,
                height: 72,
                clipBehavior: Clip.antiAlias,
                decoration: BoxDecoration(
                  color: const Color(0xFFF7F9F7),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.border),
                ),
                child: Image.memory(
                  selectedImages[index].bytes,
                  fit: BoxFit.cover,
                ),
              ),
              Positioned(
                top: -8,
                right: -8,
                child: IconButton.filled(
                  onPressed: onRemoveImage == null
                      ? null
                      : () => onRemoveImage!(index),
                  style: IconButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: AppColors.danger,
                    fixedSize: const Size(28, 28),
                    padding: EdgeInsets.zero,
                    side: const BorderSide(color: AppColors.border),
                  ),
                  icon: const Icon(Icons.close_rounded, size: 16),
                ),
              ),
            ],
          );
        },
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

class _ManualCharacteristicsPanel extends StatelessWidget {
  const _ManualCharacteristicsPanel({
    required this.value,
    required this.enabled,
    required this.onChanged,
  });

  final QualityManualInputs value;
  final bool enabled;
  final ValueChanged<QualityManualInputs> onChanged;

  @override
  Widget build(BuildContext context) {
    return ExpansionTile(
      tilePadding: const EdgeInsets.symmetric(horizontal: 14),
      childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
      shape: RoundedRectangleBorder(
        side: const BorderSide(color: AppColors.border),
        borderRadius: BorderRadius.circular(18),
      ),
      collapsedShape: RoundedRectangleBorder(
        side: const BorderSide(color: AppColors.border),
        borderRadius: BorderRadius.circular(18),
      ),
      backgroundColor: Colors.white,
      collapsedBackgroundColor: Colors.white,
      title: const Text(
        'Optional leaf characteristics',
        style: TextStyle(
          color: AppColors.text,
          fontWeight: FontWeight.w900,
        ),
      ),
      subtitle: const Text(
        'Used only as maturity-stage support.',
        style: TextStyle(
          color: AppColors.muted,
          fontWeight: FontWeight.w700,
        ),
      ),
      children: [
        Row(
          children: [
            Expanded(
              child: _ManualNumberField(
                label: 'Length cm',
                enabled: enabled,
                onChanged: (leafLengthCm) => onChanged(
                  value.copyWith(leafLengthCm: leafLengthCm),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _ManualNumberField(
                label: 'Width cm',
                enabled: enabled,
                onChanged: (leafWidthCm) => onChanged(
                  value.copyWith(leafWidthCm: leafWidthCm),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        _ManualOptionGrid(
          enabled: enabled,
          value: value,
          onChanged: onChanged,
        ),
      ],
    );
  }
}

class _ManualNumberField extends StatelessWidget {
  const _ManualNumberField({
    required this.label,
    required this.enabled,
    required this.onChanged,
  });

  final String label;
  final bool enabled;
  final ValueChanged<double?> onChanged;

  @override
  Widget build(BuildContext context) {
    return TextField(
      enabled: enabled,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(fontWeight: FontWeight.w700),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        isDense: true,
      ),
      onChanged: (value) => onChanged(double.tryParse(value.trim())),
    );
  }
}

class _ManualOptionGrid extends StatelessWidget {
  const _ManualOptionGrid({
    required this.enabled,
    required this.value,
    required this.onChanged,
  });

  final bool enabled;
  final QualityManualInputs value;
  final ValueChanged<QualityManualInputs> onChanged;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        _ManualDropdown(
          label: 'Texture',
          value: value.leafTexture,
          enabled: enabled,
          items: const ['Unknown', 'Smooth', 'Slightly_Rough', 'Rough'],
          onChanged: (leafTexture) => onChanged(
            value.copyWith(leafTexture: leafTexture),
          ),
        ),
        _ManualDropdown(
          label: 'Edge',
          value: value.leafEdge,
          enabled: enabled,
          items: const ['Unknown', 'Smooth', 'Serrated', 'Irregular'],
          onChanged: (leafEdge) => onChanged(value.copyWith(leafEdge: leafEdge)),
        ),
        _ManualDropdown(
          label: 'Spots',
          value: value.surfaceSpots,
          enabled: enabled,
          items: const ['Unknown', 'None', 'Few', 'Many'],
          onChanged: (surfaceSpots) => onChanged(
            value.copyWith(surfaceSpots: surfaceSpots),
          ),
        ),
        _ManualDropdown(
          label: 'Holes',
          value: value.holes,
          enabled: enabled,
          items: const ['Unknown', 'None', 'Few', 'Many'],
          onChanged: (holes) => onChanged(value.copyWith(holes: holes)),
        ),
        _ManualDropdown(
          label: 'Discoloration',
          value: value.discoloration,
          enabled: enabled,
          items: const ['Unknown', 'None', 'Yellow', 'Brown', 'Purple', 'Mixed'],
          onChanged: (discoloration) => onChanged(
            value.copyWith(discoloration: discoloration),
          ),
        ),
      ],
    );
  }
}

class _ManualDropdown extends StatelessWidget {
  const _ManualDropdown({
    required this.label,
    required this.value,
    required this.enabled,
    required this.items,
    required this.onChanged,
  });

  final String label;
  final String value;
  final bool enabled;
  final List<String> items;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 160,
      child: DropdownButtonFormField<String>(
        value: value,
        isExpanded: true,
        decoration: InputDecoration(
          labelText: label,
          labelStyle: const TextStyle(fontWeight: FontWeight.w700),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          isDense: true,
        ),
        items: items
            .map(
              (item) => DropdownMenuItem(
                value: item,
                child: Text(
                  item.replaceAll('_', ' '),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            )
            .toList(),
        onChanged: enabled
            ? (selected) {
                if (selected != null) {
                  onChanged(selected);
                }
              }
            : null,
      ),
    );
  }
}

class _ValidationPanel extends StatelessWidget {
  const _ValidationPanel({
    required this.result,
  });

  final QualityValidationResult? result;

  @override
  Widget build(BuildContext context) {
    if (result != null && !result!.valid) {
      return _StatusPanel(
        icon: const Icon(Icons.error_outline_rounded, color: AppColors.danger),
        title: _reasonTitle(result!.reason),
        subtitle: _reasonHelp(result!.reason),
      );
    }

    return const SizedBox.shrink();
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
    this.subtitle,
    this.heading,
    this.result,
    this.plantResult,
    this.conditionResult,
  });

  final Widget icon;
  final String title;
  final String? subtitle;
  final String? heading;
  final QualityValidationResult? result;
  final QualityPlantResult? plantResult;
  final QualityConditionResult? conditionResult;

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
          if (heading != null && heading!.isNotEmpty) ...[
            Text(
              heading!,
              style: const TextStyle(
                color: AppColors.text,
                fontSize: 22,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 14),
          ],
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
                    if (subtitle != null && subtitle!.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        subtitle!,
                        style: const TextStyle(
                          color: AppColors.muted,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
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
          if (conditionResult != null) ...[
            const SizedBox(height: 14),
            _ConditionResultDetails(
              result: conditionResult!,
              plantResult: plantResult,
            ),
          ],
        ],
      ),
    );
  }
}

class _ConditionResultDetails extends StatelessWidget {
  const _ConditionResultDetails({
    required this.result,
    this.plantResult,
  });

  final QualityConditionResult result;
  final QualityPlantResult? plantResult;

  @override
  Widget build(BuildContext context) {
    final condition = result.condition;
    final diseaseInfo = result.diseaseInfo;
    final maturity = result.maturity;
    final medicinalSuitability = result.medicinalSuitability;
    final xai = result.xai;

    if (condition == null) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ConditionSummaryGrid(
          status: _statusLabel(condition.status),
          conditionClass: condition.displayName,
        ),
        if (condition.mode == 'mock') ...[
          const SizedBox(height: 10),
          const Text(
            'Mock condition prediction active until a trained model is configured.',
            style: TextStyle(
              color: AppColors.muted,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
        if (diseaseInfo != null) ...[
          const SizedBox(height: 14),
          _DiseaseInfoView(
            info: diseaseInfo,
            plantName: plantResult?.species,
            conditionName: condition.displayName,
          ),
        ],
        if (maturity != null && maturity.shouldDisplay) ...[
          const SizedBox(height: 14),
          _MaturityInfoView(maturity: maturity),
        ] else if (medicinalSuitability != null) ...[
          const SizedBox(height: 14),
          _MedicinalSuitabilitySummary(info: medicinalSuitability),
        ],
        if (xai != null && xai.shouldDisplay) ...[
          const SizedBox(height: 14),
          _XaiExplanationView(
            xai: xai,
            condition: condition,
          ),
        ],
      ],
    );
  }

  String _statusLabel(String status) {
    return status == 'diseased' ? 'Condition detected' : status;
  }
}

class _ConditionSummaryGrid extends StatelessWidget {
  const _ConditionSummaryGrid({
    required this.status,
    required this.conditionClass,
  });

  final String status;
  final String conditionClass;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final useColumns = constraints.maxWidth >= 360;
        final chips = [
          _FlexibleMetricChip(label: 'Status', value: status),
          _FlexibleMetricChip(label: 'Class', value: conditionClass),
        ];

        if (!useColumns) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              chips[0],
              const SizedBox(height: 10),
              chips[1],
            ],
          );
        }

        return IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(child: chips[0]),
              const SizedBox(width: 12),
              Expanded(child: chips[1]),
            ],
          ),
        );
      },
    );
  }
}

class _FlexibleMetricChip extends StatelessWidget {
  const _FlexibleMetricChip({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: 78),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
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
          const SizedBox(height: 6),
          Text(
            value,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: AppColors.text,
              fontSize: 16,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _XaiExplanationView extends StatefulWidget {
  const _XaiExplanationView({
    required this.xai,
    this.condition,
  });

  final QualityXaiResult xai;
  final QualityConditionPrediction? condition;

  @override
  State<_XaiExplanationView> createState() => _XaiExplanationViewState();
}

class _XaiExplanationViewState extends State<_XaiExplanationView> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final xai = widget.xai;
    final gradcam = xai.gradcam;
    final shap = xai.shap;
    final technicalItems = _technicalItems(gradcam: gradcam, shap: shap);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                children: [
                  Icon(
                    _expanded
                        ? Icons.expand_less_rounded
                        : Icons.expand_more_rounded,
                    color: AppColors.text,
                  ),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'View technical explanation',
                      style: TextStyle(
                        color: AppColors.text,
                        fontSize: 15,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (_expanded) ...[
            if (technicalItems.isNotEmpty) ...[
              const SizedBox(height: 12),
              _TechnicalMetricGrid(items: technicalItems),
            ],
            if (gradcam != null &&
                gradcam.available &&
                gradcam.base64Image.isNotEmpty) ...[
              const SizedBox(height: 12),
              _DiseaseInfoSection(
                title: 'Grad-CAM Heatmap',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(10),
                      child: Image.memory(
                        base64Decode(gradcam.base64Image),
                        width: double.infinity,
                        fit: BoxFit.contain,
                      ),
                    ),
                    const SizedBox(height: 8),
                    _DiseaseParagraph(gradcam.message),
                    if (gradcam.limitation.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      _DiseaseParagraph(gradcam.limitation),
                    ],
                  ],
                ),
              ),
            ],
            if (shap != null && shap.available) ...[
              const SizedBox(height: 12),
              _DiseaseInfoSection(
                title: 'Structured Feature Influence',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _DiseaseParagraph(shap.message),
                    const SizedBox(height: 8),
                    _DiseaseBulletList(
                      items: shap.features
                          .map(
                            (feature) =>
                                '${feature.feature}: ${feature.effect} - ${feature.description}',
                          )
                          .toList(),
                    ),
                    if (shap.limitation.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      _DiseaseParagraph(shap.limitation),
                    ],
                  ],
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }

  List<_TechnicalMetric> _technicalItems({
    required QualityGradCamExplanation? gradcam,
    required QualityStructuredExplanation? shap,
  }) {
    final condition = widget.condition;

    return [
      if (condition != null)
        _TechnicalMetric(
          label: 'Prediction',
          value: condition.displayName,
        ),
      if (condition != null)
        _TechnicalMetric(
          label: 'Status',
          value: condition.status,
        ),
      if (condition != null)
        _TechnicalMetric(
          label: 'Confidence',
          value: condition.confidencePercent,
        ),
      if (condition != null &&
          condition.model != null &&
          condition.model!.isNotEmpty)
        _TechnicalMetric(label: 'Model', value: condition.model!),
      if (condition != null && condition.imageCount != null)
        _TechnicalMetric(
          label: 'Images',
          value: '${condition.imageCount} used',
        ),
      if (condition != null &&
          condition.mode != null &&
          condition.mode!.isNotEmpty)
        _TechnicalMetric(label: 'Mode', value: condition.mode!),
      if (widget.xai.finalStage.isNotEmpty)
        _TechnicalMetric(label: 'XAI stage', value: widget.xai.finalStage),
      if (gradcam != null)
        _TechnicalMetric(
          label: 'Grad-CAM',
          value: gradcam.available ? 'Available' : 'Unavailable',
        ),
      if (shap != null)
        _TechnicalMetric(
          label: 'Structured features',
          value:
              shap.available ? '${shap.features.length} used' : 'Unavailable',
        ),
    ];
  }
}

class _TechnicalMetric {
  const _TechnicalMetric({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;
}

class _TechnicalMetricGrid extends StatelessWidget {
  const _TechnicalMetricGrid({required this.items});

  final List<_TechnicalMetric> items;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final useColumns = constraints.maxWidth >= 360;

        if (!useColumns) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (var index = 0; index < items.length; index++) ...[
                _FlexibleMetricChip(
                  label: items[index].label,
                  value: items[index].value,
                ),
                if (index != items.length - 1) const SizedBox(height: 10),
              ],
            ],
          );
        }

        final rows = <Widget>[];
        for (var index = 0; index < items.length; index += 2) {
          final secondIndex = index + 1;
          rows.add(
            IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(
                    child: _FlexibleMetricChip(
                      label: items[index].label,
                      value: items[index].value,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: secondIndex < items.length
                        ? _FlexibleMetricChip(
                            label: items[secondIndex].label,
                            value: items[secondIndex].value,
                          )
                        : const SizedBox.shrink(),
                  ),
                ],
              ),
            ),
          );
        }

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (var index = 0; index < rows.length; index++) ...[
              rows[index],
              if (index != rows.length - 1) const SizedBox(height: 10),
            ],
          ],
        );
      },
    );
  }
}

class _MaturityInfoView extends StatelessWidget {
  const _MaturityInfoView({required this.maturity});

  final QualityMaturityResult maturity;

  @override
  Widget build(BuildContext context) {
    final decision = maturity.finalDecision;
    final prediction = maturity.modelPrediction;
    final manualSupport = maturity.manualSupport;
    final suitability = maturity.medicinalSuitability;
    final details = maturity.maturityInfo;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Maturity',
            style: TextStyle(
              color: AppColors.text,
              fontSize: 15,
              fontWeight: FontWeight.w900,
            ),
          ),
          if (decision.stageDisplay.isNotEmpty) ...[
            const SizedBox(height: 10),
            _MetricChip(label: 'Stage', value: decision.stageDisplay),
          ],
          if (prediction != null) ...[
            const SizedBox(height: 10),
            _MetricChip(
              label: 'Confidence',
              value: prediction.confidencePercent,
            ),
          ],
          if (manualSupport != null && manualSupport.evidence.isNotEmpty) ...[
            const SizedBox(height: 12),
            _DiseaseInfoSection(
              title: 'Supporting Characteristics',
              child: _DiseaseBulletList(items: manualSupport.evidence),
            ),
          ],
          if (details != null && details.visualCharacteristics.isNotEmpty) ...[
            const SizedBox(height: 12),
            _DiseaseInfoSection(
              title: 'Reference Characteristics',
              child: _DiseaseBulletList(
                items: _splitDisplayItems(details.visualCharacteristics),
              ),
            ),
          ],
          if (suitability != null) ...[
            const SizedBox(height: 12),
            _MedicinalSuitabilitySummary(info: suitability),
          ],
        ],
      ),
    );
  }

  List<String> _splitDisplayItems(String value) {
    return value
        .split(value.contains(';') ? ';' : '. ')
        .map((item) => item.trim())
        .where((item) => item.isNotEmpty)
        .toList();
  }
}

class _MedicinalSuitabilitySummary extends StatelessWidget {
  const _MedicinalSuitabilitySummary({required this.info});

  final QualityMedicinalSuitability info;

  @override
  Widget build(BuildContext context) {
    return _DiseaseInfoSection(
      title: 'Medicinal Suitability',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _MedicinalSuitabilityBar(level: info.level),
          const SizedBox(height: 8),
          Text(
            info.display,
            style: const TextStyle(
              color: AppColors.text,
              fontWeight: FontWeight.w900,
            ),
          ),
          if (info.assessment.isNotEmpty) ...[
            const SizedBox(height: 6),
            _DiseaseParagraph(info.assessment),
          ],
        ],
      ),
    );
  }
}

class _DiseaseInfoView extends StatefulWidget {
  const _DiseaseInfoView({
    required this.info,
    this.plantName,
    this.conditionName,
  });

  final QualityDiseaseInfo info;
  final String? plantName;
  final String? conditionName;

  @override
  State<_DiseaseInfoView> createState() => _DiseaseInfoViewState();
}

class _DiseaseInfoViewState extends State<_DiseaseInfoView> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final info = widget.info;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            info.displayName,
            style: const TextStyle(
              color: AppColors.text,
              fontSize: 15,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 12),
          _MedicinalSuitabilityBar(
            level: info.medicinalSuitabilityLevel,
          ),
          const SizedBox(height: 12),
          _DiseaseInfoSection(
            title: 'Description',
            child: _DiseaseParagraph(info.description),
          ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: () => setState(() => _expanded = !_expanded),
              icon: Icon(
                _expanded
                    ? Icons.expand_less_rounded
                    : Icons.expand_more_rounded,
                size: 20,
              ),
              label: Text(_expanded ? 'Less' : 'More'),
              style: TextButton.styleFrom(
                foregroundColor: AppColors.primary,
                padding: EdgeInsets.zero,
                textStyle: const TextStyle(fontWeight: FontWeight.w900),
              ),
            ),
          ),
          if (_expanded) ...[
            if (info.medicinalSuitabilityAssessment.isNotEmpty) ...[
              const SizedBox(height: 8),
              _DiseaseInfoSection(
                title: 'Medicinal Suitability Assessment',
                child: _DiseaseBulletList(
                  items: _splitDisplayItems(
                    info.medicinalSuitabilityAssessment,
                  ),
                ),
              ),
            ],
            if (info.typicalSymptoms.isNotEmpty) ...[
              const SizedBox(height: 12),
              _DiseaseInfoSection(
                title: 'Typical Symptoms',
                child: _DiseaseBulletList(items: info.typicalSymptoms),
              ),
            ],
            if (info.healthyDifference.isNotEmpty) ...[
              const SizedBox(height: 12),
              _DiseaseInfoSection(
                title: 'Healthy Difference',
                child: _DiseaseBulletList(
                  items: _splitDisplayItems(info.healthyDifference),
                ),
              ),
            ],
            if (info.medicinalUseInstruction.isNotEmpty) ...[
              const SizedBox(height: 12),
              _DiseaseInfoSection(
                title: 'Medicinal Use Instruction',
                child: _DiseaseBulletList(
                  items: _splitDisplayItems(info.medicinalUseInstruction),
                ),
              ),
            ],
            if (info.treatmentInstruction.isNotEmpty) ...[
              const SizedBox(height: 12),
              _DiseaseInfoSection(
                title: 'Treatment Instruction',
                child: _DiseaseBulletList(
                  items: _splitDisplayItems(info.treatmentInstruction),
                ),
              ),
            ],
            if (info.reference.isNotEmpty) ...[
              const SizedBox(height: 12),
              _DiseaseInfoSection(
                title: 'Reference',
                child: _DiseaseBulletList(
                  items: info.reference
                      .split('|')
                      .map((reference) => reference.trim())
                      .where((reference) => reference.isNotEmpty)
                      .toList(),
                ),
              ),
            ],
            const SizedBox(height: 14),
            Center(
              child: TextButton(
                onPressed: _openGeneralPublicLearnMore,
                style: TextButton.styleFrom(
                  foregroundColor: const Color(0xFF7ACB8A),
                  textStyle: const TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 14,
                  ),
                ),
                child: const Text('Learn more'),
              ),
            ),
          ],
        ],
      ),
    );
  }

  void _openGeneralPublicLearnMore() {
    final message = [
      widget.plantName,
      widget.conditionName,
    ]
        .whereType<String>()
        .map((part) => part.trim())
        .where((part) => part.isNotEmpty)
        .join(' ');

    if (message.isEmpty) {
      return;
    }

    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => GeneralPublicChatPage(initialMessage: message),
      ),
    );
  }

  List<String> _splitDisplayItems(String value) {
    final separator = value.contains(';') ? ';' : '. ';
    return value
        .split(separator)
        .map((item) => item.trim())
        .where((item) => item.isNotEmpty)
        .map((item) {
      if (separator == '. ' && !item.endsWith('.')) {
        return '$item.';
      }
      return item;
    }).toList();
  }
}

class _DiseaseInfoSection extends StatelessWidget {
  const _DiseaseInfoSection({
    required this.title,
    required this.child,
  });

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            color: AppColors.text,
            fontSize: 13,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 5),
        child,
      ],
    );
  }
}

class _DiseaseParagraph extends StatelessWidget {
  const _DiseaseParagraph(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: AppColors.muted,
        fontWeight: FontWeight.w700,
      ),
    );
  }
}

class _DiseaseBulletList extends StatelessWidget {
  const _DiseaseBulletList({required this.items});

  final List<String> items;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: items
          .map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 5),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Padding(
                    padding: EdgeInsets.only(top: 8),
                    child: SizedBox(
                      width: 5,
                      height: 5,
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: AppColors.primary,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      item,
                      style: const TextStyle(
                        color: AppColors.muted,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          )
          .toList(),
    );
  }
}

class _MedicinalSuitabilityBar extends StatelessWidget {
  const _MedicinalSuitabilityBar({
    required this.level,
  });

  final String level;

  @override
  Widget build(BuildContext context) {
    final normalizedLevel = level.trim().toLowerCase().replaceAll(' ', '_');
    final style = _styleForLevel(normalizedLevel);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                _displayLevel(level),
                style: TextStyle(
                  color: style.color,
                  fontSize: 13,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            Text(
              '${(style.value * 100).round()}%',
              style: const TextStyle(
                color: AppColors.muted,
                fontSize: 12,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            minHeight: 9,
            value: style.value,
            color: style.color,
            backgroundColor: const Color(0xFFE8ECE8),
          ),
        ),
      ],
    );
  }

  _SuitabilityStyle _styleForLevel(String level) {
    switch (level) {
      case 'suitable':
      case 'high_suitability':
        return const _SuitabilityStyle(Color(0xFF22C55E), 1);
      case 'conditionally_suitable':
      case 'moderate_suitability':
        return const _SuitabilityStyle(Color(0xFFEAB308), 0.67);
      case 'low_suitability':
        return const _SuitabilityStyle(Color(0xFFF97316), 0.34);
      case 'not_recommended':
      case 'unsuitable':
        return const _SuitabilityStyle(Color(0xFFEF4444), 0.12);
      default:
        return const _SuitabilityStyle(Color(0xFF64748B), 0.5);
    }
  }

  String _displayLevel(String value) {
    final text = value.trim().replaceAll('_', ' ');
    if (text.isEmpty) {
      return 'Expert Verification Recommended';
    }

    return text
        .split(' ')
        .where((word) => word.isNotEmpty)
        .map((word) => '${word[0].toUpperCase()}${word.substring(1)}')
        .join(' ');
  }
}

class _SuitabilityStyle {
  const _SuitabilityStyle(this.color, this.value);

  final Color color;
  final double value;
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
            if (result.imageCount != null)
              _MetricChip(label: 'Images', value: '${result.imageCount} used'),
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

  factory QualityValidationResult.combinedSuccess(
    List<QualityValidationResult> results,
  ) {
    QualityImageResolution? firstResolution;
    for (final result in results) {
      if (result.resolution != null) {
        firstResolution = result.resolution;
        break;
      }
    }
    final blurScores = results
        .where((result) => result.blurScore != null)
        .map((result) => result.blurScore!)
        .toList();
    final brightnessValues = results
        .where((result) => result.brightness != null)
        .map((result) => result.brightness!)
        .toList();

    return QualityValidationResult(
      valid: true,
      resolution: firstResolution,
      blurScore: blurScores.isEmpty
          ? null
          : blurScores.reduce((a, b) => a + b) / blurScores.length,
      brightness: brightnessValues.isEmpty
          ? null
          : brightnessValues.reduce((a, b) => a + b) / brightnessValues.length,
    );
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
    this.imageCount,
    this.aggregation,
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
      imageCount: (json['image_count'] as num?)?.toInt(),
      aggregation: json['aggregation'] as String?,
    );
  }

  final String species;
  final String? scientificName;
  final double confidence;
  final bool accepted;
  final String? reason;
  final String? model;
  final String? mode;
  final int? imageCount;
  final String? aggregation;

  String get confidencePercent => '${(confidence * 100).toStringAsFixed(1)}%';
}

class QualityConditionResult {
  const QualityConditionResult({
    required this.accepted,
    this.reason,
    this.condition,
    this.diseaseInfo,
    this.maturity,
    this.medicinalSuitability,
    this.xai,
  });

  factory QualityConditionResult.failure({required String reason}) {
    return QualityConditionResult(accepted: false, reason: reason);
  }

  factory QualityConditionResult.fromJson(Map<String, dynamic> json) {
    final conditionJson = json['condition'] as Map<String, dynamic>?;
    final diseaseInfoJson = json['disease_info'] as Map<String, dynamic>?;
    final maturityJson = json['maturity'] as Map<String, dynamic>?;
    final medicinalSuitabilityJson =
        json['medicinal_suitability'] as Map<String, dynamic>?;
    final xaiJson = json['xai'] as Map<String, dynamic>?;

    return QualityConditionResult(
      accepted: json['accepted'] == true,
      reason: json['reason'] as String?,
      condition: conditionJson == null
          ? null
          : QualityConditionPrediction.fromJson(conditionJson),
      diseaseInfo: diseaseInfoJson == null
          ? null
          : QualityDiseaseInfo.fromJson(diseaseInfoJson),
      maturity: maturityJson == null
          ? null
          : QualityMaturityResult.fromJson(maturityJson),
      medicinalSuitability: medicinalSuitabilityJson == null
          ? null
          : QualityMedicinalSuitability.fromJson(medicinalSuitabilityJson),
      xai: xaiJson == null ? null : QualityXaiResult.fromJson(xaiJson),
    );
  }

  final bool accepted;
  final String? reason;
  final QualityConditionPrediction? condition;
  final QualityDiseaseInfo? diseaseInfo;
  final QualityMaturityResult? maturity;
  final QualityMedicinalSuitability? medicinalSuitability;
  final QualityXaiResult? xai;
}

class QualityConditionPrediction {
  const QualityConditionPrediction({
    required this.status,
    required this.className,
    required this.displayName,
    required this.confidence,
    this.reason,
    this.model,
    this.mode,
    this.imageCount,
  });

  factory QualityConditionPrediction.fromJson(Map<String, dynamic> json) {
    return QualityConditionPrediction(
      status: (json['status'] as String?) ?? 'unavailable',
      className: (json['class'] as String?) ?? '',
      displayName: (json['display_name'] as String?) ??
          ((json['class'] as String?) ?? '').replaceAll('_', ' '),
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      reason: json['reason'] as String?,
      model: json['model'] as String?,
      mode: json['mode'] as String?,
      imageCount: (json['image_count'] as num?)?.toInt(),
    );
  }

  final String status;
  final String className;
  final String displayName;
  final double confidence;
  final String? reason;
  final String? model;
  final String? mode;
  final int? imageCount;

  String get confidencePercent => '${(confidence * 100).toStringAsFixed(1)}%';
}

class QualityDiseaseInfo {
  const QualityDiseaseInfo({
    required this.found,
    required this.displayName,
    required this.description,
    required this.typicalSymptoms,
    required this.healthyDifference,
    required this.medicinalUseInstruction,
    required this.treatmentInstruction,
    required this.medicinalSuitabilityLevel,
    required this.medicinalSuitabilityAssessment,
    required this.reference,
  });

  factory QualityDiseaseInfo.fromJson(Map<String, dynamic> json) {
    return QualityDiseaseInfo(
      found: json['found'] == true,
      displayName: (json['display_name'] as String?) ??
          'Disease information unavailable',
      description: (json['description'] as String?) ?? '',
      typicalSymptoms: (json['typical_symptoms'] as List<dynamic>?)
              ?.map((symptom) => symptom.toString())
              .toList() ??
          [],
      healthyDifference: (json['healthy_difference'] as String?) ?? '',
      medicinalUseInstruction:
          (json['medicinal_use_instruction'] as String?) ??
              (json['instructions'] as String?) ??
          'Expert verification recommended.',
      treatmentInstruction: (json['treatment_instruction'] as String?) ?? '',
      medicinalSuitabilityLevel:
          (json['medicinal_suitability_level'] as String?) ??
              'Expert_Verification_Recommended',
      medicinalSuitabilityAssessment:
          (json['medicinal_suitability_assessment'] as String?) ??
              'Expert verification recommended.',
      reference: (json['reference'] as String?) ?? '',
    );
  }

  final bool found;
  final String displayName;
  final String description;
  final List<String> typicalSymptoms;
  final String healthyDifference;
  final String medicinalUseInstruction;
  final String treatmentInstruction;
  final String medicinalSuitabilityLevel;
  final String medicinalSuitabilityAssessment;
  final String reference;
}

class QualityMaturityResult {
  const QualityMaturityResult({
    this.modelPrediction,
    this.manualSupport,
    required this.finalDecision,
    this.maturityInfo,
    this.medicinalSuitability,
    this.reason,
    this.model,
    this.mode,
  });

  factory QualityMaturityResult.fromJson(Map<String, dynamic> json) {
    final modelPredictionJson =
        json['model_prediction'] as Map<String, dynamic>?;
    final manualSupportJson = json['manual_support'] as Map<String, dynamic>?;
    final finalDecisionJson =
        json['final_decision'] as Map<String, dynamic>? ?? {};
    final maturityInfoJson = json['maturity_info'] as Map<String, dynamic>?;
    final suitabilityJson =
        json['medicinal_suitability'] as Map<String, dynamic>?;

    return QualityMaturityResult(
      modelPrediction: modelPredictionJson == null
          ? null
          : QualityMaturityPrediction.fromJson(modelPredictionJson),
      manualSupport: manualSupportJson == null
          ? null
          : QualityManualSupport.fromJson(manualSupportJson),
      finalDecision: QualityMaturityDecision.fromJson(finalDecisionJson),
      maturityInfo: maturityInfoJson == null
          ? null
          : QualityMaturityInfo.fromJson(maturityInfoJson),
      medicinalSuitability: suitabilityJson == null
          ? null
          : QualityMedicinalSuitability.fromJson(suitabilityJson),
      reason: json['reason'] as String?,
      model: json['model'] as String?,
      mode: json['mode'] as String?,
    );
  }

  final QualityMaturityPrediction? modelPrediction;
  final QualityManualSupport? manualSupport;
  final QualityMaturityDecision finalDecision;
  final QualityMaturityInfo? maturityInfo;
  final QualityMedicinalSuitability? medicinalSuitability;
  final String? reason;
  final String? model;
  final String? mode;

  bool get shouldDisplay =>
      finalDecision.stageDisplay.isNotEmpty || modelPrediction != null;
}

class QualityMaturityPrediction {
  const QualityMaturityPrediction({
    required this.stage,
    this.canonicalStage,
    required this.confidence,
  });

  factory QualityMaturityPrediction.fromJson(Map<String, dynamic> json) {
    return QualityMaturityPrediction(
      stage: (json['stage'] as String?) ?? '',
      canonicalStage: json['canonical_stage'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
    );
  }

  final String stage;
  final String? canonicalStage;
  final double confidence;

  String get confidencePercent => '${(confidence * 100).toStringAsFixed(1)}%';
}

class QualityMaturityDecision {
  const QualityMaturityDecision({
    this.stage,
    this.canonicalStage,
    this.decisionStatus,
    this.reason,
  });

  factory QualityMaturityDecision.fromJson(Map<String, dynamic> json) {
    return QualityMaturityDecision(
      stage: json['stage'] as String?,
      canonicalStage: json['canonical_stage'] as String?,
      decisionStatus: json['decision_status'] as String?,
      reason: json['reason'] as String?,
    );
  }

  final String? stage;
  final String? canonicalStage;
  final String? decisionStatus;
  final String? reason;

  String get stageDisplay {
    final value = canonicalStage ?? stage ?? '';
    final normalized = value.toLowerCase();
    if (value.isEmpty ||
        normalized == 'unknown' ||
        normalized == 'null' ||
        normalized == 'not_assessed' ||
        normalized == 'uncertain') {
      return '';
    }

    return value.replaceAll('_', ' ');
  }
}

class QualityManualSupport {
  const QualityManualSupport({
    required this.used,
    required this.availableFeatures,
    required this.evidence,
  });

  factory QualityManualSupport.fromJson(Map<String, dynamic> json) {
    return QualityManualSupport(
      used: json['used'] == true,
      availableFeatures: (json['available_features'] as num?)?.toInt() ?? 0,
      evidence: (json['evidence'] as List<dynamic>?)
              ?.map((item) => item.toString())
              .toList() ??
          [],
    );
  }

  final bool used;
  final int availableFeatures;
  final List<String> evidence;
}

class QualityMaturityInfo {
  const QualityMaturityInfo({
    required this.visualCharacteristics,
  });

  factory QualityMaturityInfo.fromJson(Map<String, dynamic> json) {
    return QualityMaturityInfo(
      visualCharacteristics: (json['visual_characteristics'] as String?) ?? '',
    );
  }

  final String visualCharacteristics;
}

class QualityMedicinalSuitability {
  const QualityMedicinalSuitability({
    required this.level,
    required this.display,
    required this.assessment,
    required this.evidenceStrength,
  });

  factory QualityMedicinalSuitability.fromJson(Map<String, dynamic> json) {
    return QualityMedicinalSuitability(
      level: (json['level'] as String?) ?? 'Expert_Verification_Recommended',
      display: (json['display'] as String?) ??
          'Expert verification recommended before medicinal use',
      assessment: (json['assessment'] as String?) ?? '',
      evidenceStrength: (json['evidence_strength'] as String?) ?? '',
    );
  }

  final String level;
  final String display;
  final String assessment;
  final String evidenceStrength;
}

class QualityXaiResult {
  const QualityXaiResult({
    required this.finalStage,
    this.gradcam,
    this.shap,
  });

  factory QualityXaiResult.fromJson(Map<String, dynamic> json) {
    final gradcamJson = json['gradcam'] as Map<String, dynamic>?;
    final shapJson = json['shap'] as Map<String, dynamic>?;

    return QualityXaiResult(
      finalStage: (json['final_stage'] as String?) ?? '',
      gradcam: gradcamJson == null
          ? null
          : QualityGradCamExplanation.fromJson(gradcamJson),
      shap: shapJson == null
          ? null
          : QualityStructuredExplanation.fromJson(shapJson),
    );
  }

  final String finalStage;
  final QualityGradCamExplanation? gradcam;
  final QualityStructuredExplanation? shap;

  bool get shouldDisplay =>
      (gradcam != null &&
          gradcam!.available &&
          gradcam!.base64Image.isNotEmpty) ||
      (shap != null && shap!.available);
}

class QualityGradCamExplanation {
  const QualityGradCamExplanation({
    required this.available,
    required this.base64Image,
    required this.message,
    required this.limitation,
  });

  factory QualityGradCamExplanation.fromJson(Map<String, dynamic> json) {
    return QualityGradCamExplanation(
      available: json['available'] == true,
      base64Image: _extractBase64Image((json['heatmap_image'] as String?) ?? ''),
      message: (json['message'] as String?) ??
          'The highlighted regions had the greatest influence on the AI prediction.',
      limitation: (json['limitation'] as String?) ?? '',
    );
  }

  final bool available;
  final String base64Image;
  final String message;
  final String limitation;

  static String _extractBase64Image(String value) {
    final commaIndex = value.indexOf(',');
    if (commaIndex == -1) {
      return value;
    }

    return value.substring(commaIndex + 1);
  }
}

class QualityStructuredExplanation {
  const QualityStructuredExplanation({
    required this.available,
    required this.message,
    required this.limitation,
    required this.features,
  });

  factory QualityStructuredExplanation.fromJson(Map<String, dynamic> json) {
    return QualityStructuredExplanation(
      available: json['available'] == true,
      message: (json['message'] as String?) ??
          'Manual characteristics influenced the maturity decision.',
      limitation: (json['limitation'] as String?) ?? '',
      features: (json['features'] as List<dynamic>?)
              ?.whereType<Map<String, dynamic>>()
              .map(QualityStructuredFeatureInfluence.fromJson)
              .toList() ??
          [],
    );
  }

  final bool available;
  final String message;
  final String limitation;
  final List<QualityStructuredFeatureInfluence> features;
}

class QualityStructuredFeatureInfluence {
  const QualityStructuredFeatureInfluence({
    required this.feature,
    required this.effect,
    required this.description,
  });

  factory QualityStructuredFeatureInfluence.fromJson(
    Map<String, dynamic> json,
  ) {
    return QualityStructuredFeatureInfluence(
      feature: (json['feature'] as String?) ?? 'Manual characteristic',
      effect: (json['effect'] as String?) ?? 'used',
      description: (json['description'] as String?) ?? '',
    );
  }

  final String feature;
  final String effect;
  final String description;
}

class QualityManualInputs {
  const QualityManualInputs({
    this.leafLengthCm,
    this.leafWidthCm,
    this.leafTexture = 'Unknown',
    this.leafEdge = 'Unknown',
    this.surfaceSpots = 'Unknown',
    this.holes = 'Unknown',
    this.discoloration = 'Unknown',
  });

  final double? leafLengthCm;
  final double? leafWidthCm;
  final String leafTexture;
  final String leafEdge;
  final String surfaceSpots;
  final String holes;
  final String discoloration;

  bool get hasValues => toJson().isNotEmpty;

  Map<String, dynamic> toJson() {
    final json = <String, dynamic>{};
    if (leafLengthCm != null) {
      json['leaf_length_cm'] = leafLengthCm;
    }
    if (leafWidthCm != null) {
      json['leaf_width_cm'] = leafWidthCm;
    }
    _addKnown(json, 'leaf_texture', leafTexture);
    _addKnown(json, 'leaf_edge', leafEdge);
    _addKnown(json, 'surface_spots', surfaceSpots);
    _addKnown(json, 'holes', holes);
    _addKnown(json, 'discoloration', discoloration);
    return json;
  }

  QualityManualInputs copyWith({
    Object? leafLengthCm = _manualUnset,
    Object? leafWidthCm = _manualUnset,
    String? leafTexture,
    String? leafEdge,
    String? surfaceSpots,
    String? holes,
    String? discoloration,
  }) {
    final nextLeafLengthCm =
        leafLengthCm == _manualUnset ? this.leafLengthCm : leafLengthCm as double?;
    final nextLeafWidthCm =
        leafWidthCm == _manualUnset ? this.leafWidthCm : leafWidthCm as double?;

    return QualityManualInputs(
      leafLengthCm: nextLeafLengthCm,
      leafWidthCm: nextLeafWidthCm,
      leafTexture: leafTexture ?? this.leafTexture,
      leafEdge: leafEdge ?? this.leafEdge,
      surfaceSpots: surfaceSpots ?? this.surfaceSpots,
      holes: holes ?? this.holes,
      discoloration: discoloration ?? this.discoloration,
    );
  }

  static void _addKnown(
    Map<String, dynamic> json,
    String key,
    String value,
  ) {
    if (value.trim().toLowerCase() != 'unknown') {
      json[key] = value;
    }
  }
}

const Object _manualUnset = Object();

class QualitySelectedImage {
  const QualitySelectedImage({
    required this.file,
    required this.bytes,
  });

  final XFile file;
  final Uint8List bytes;
}
