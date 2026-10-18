import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../models/plant_prediction.dart';
import '../services/plant_api.dart';
import '../theme/app_colors.dart';

class IdentifyPlantPage extends StatefulWidget {
  const IdentifyPlantPage({super.key});
  @override
  State<IdentifyPlantPage> createState() => _IdentifyPlantPageState();
}

class _IdentifyPlantPageState extends State<IdentifyPlantPage> {
  final _picker = ImagePicker();
  final _api = PlantApi();
  final List<_SelectedImage> _images = [];
  PlantPrediction? _result;
  String _modelType = 'plant';
  String? _error;
  bool _loading = false;
  int _requestId = 0;

  Future<void> _pickGallery() async {
    final files = await _picker.pickMultiImage(imageQuality: 88);
    if (files.isEmpty) return;
    final selected = <_SelectedImage>[];
    for (final file in files.take(5)) {
      selected.add(_SelectedImage(file, await file.readAsBytes()));
    }
    if (!mounted) return;
    setState(() {
      _images
        ..clear()
        ..addAll(selected);
      _result = null;
      _error = files.length > 5 ? 'Only the first 5 images were added.' : null;
    });
  }

  Future<void> _takePhoto() async {
    final file = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 88,
    );
    if (file == null) return;
    final selected = _SelectedImage(file, await file.readAsBytes());
    if (!mounted) return;
    setState(() {
      if (_images.length == 5) _images.removeAt(0);
      _images.add(selected);
      _result = null;
      _error = null;
    });
  }

  Future<void> _identify() async {
    if (_images.isEmpty) {
      setState(() => _error = 'Add at least one clear image first.');
      return;
    }
    final requestId = ++_requestId;
    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });
    try {
      final result = await _api.predict(
        _images.map((image) => image.file).toList(),
        _modelType,
      );
      if (mounted && requestId == _requestId) setState(() => _result = result);
    } catch (error) {
      if (mounted && requestId == _requestId)
        setState(() => _error = error.toString());
    } finally {
      if (mounted && requestId == _requestId) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.surface,
      appBar: AppBar(
        title: const Text('Identify Plant'),
        centerTitle: false,
        backgroundColor: AppColors.surface,
        surfaceTintColor: AppColors.surface,
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(22, 16, 22, 32),
          children: [
            const Text(
              'What are you identifying?',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 6),
            const Text(
              'Choose a detector, then add up to 5 clear photos.',
              style: TextStyle(
                color: AppColors.muted,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 18),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(
                  value: 'plant',
                  icon: Icon(Icons.eco_rounded),
                  label: Text('Leaf / plant'),
                ),
                ButtonSegment(
                  value: 'seed',
                  icon: Icon(Icons.grain_rounded),
                  label: Text('Seed / spice'),
                ),
                ButtonSegment(
                  value: 'flower',
                  icon: Icon(Icons.local_florist_rounded),
                  label: Text('Flower'),
                ),
              ],
              selected: {_modelType},
              showSelectedIcon: false,
              onSelectionChanged: _loading
                  ? null
                  : (value) => setState(() {
                      _modelType = value.first;
                      _result = null;
                      _error = null;
                    }),
            ),
            const SizedBox(height: 18),
            _PhotoArea(
              images: _images,
              onGallery: _loading ? null : _pickGallery,
              onCamera: _loading ? null : _takePhoto,
              onRemove: (index) => setState(() {
                _images.removeAt(index);
                _result = null;
              }),
            ),
            const SizedBox(height: 14),
            const _CaptureTips(),
            if (_error != null) ...[
              const SizedBox(height: 14),
              _Notice(
                text: _error!,
                color: const Color(0xFFFFE8E3),
                icon: Icons.error_outline_rounded,
              ),
            ],
            const SizedBox(height: 18),
            SizedBox(
              height: 52,
              child: FilledButton.icon(
                onPressed: _loading ? null : _identify,
                style: FilledButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
                icon: _loading
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.auto_awesome_rounded),
                label: Text(
                  _loading ? 'Identifying...' : 'Identify from photos',
                ),
              ),
            ),
            if (_result != null) ...[
              const SizedBox(height: 24),
              _PredictionCard(result: _result!),
            ],
          ],
        ),
      ),
    );
  }
}

class _SelectedImage {
  const _SelectedImage(this.file, this.bytes);
  final XFile file;
  final Uint8List bytes;
}

class _PhotoArea extends StatelessWidget {
  const _PhotoArea({
    required this.images,
    required this.onGallery,
    required this.onCamera,
    required this.onRemove,
  });
  final List<_SelectedImage> images;
  final VoidCallback? onGallery;
  final VoidCallback? onCamera;
  final ValueChanged<int> onRemove;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(20),
      border: Border.all(color: AppColors.border),
    ),
    child: Column(
      children: [
        if (images.isEmpty)
          Container(
            height: 190,
            width: double.infinity,
            decoration: BoxDecoration(
              color: const Color(0xFFEAFBF0),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.add_a_photo_rounded,
                  size: 44,
                  color: AppColors.primary,
                ),
                SizedBox(height: 10),
                Text(
                  'Add 1 to 5 photos',
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16),
                ),
                SizedBox(height: 4),
                Text(
                  'Multiple angles improve confidence',
                  style: TextStyle(color: AppColors.muted),
                ),
              ],
            ),
          )
        else
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: images.length,
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              crossAxisSpacing: 8,
              mainAxisSpacing: 8,
            ),
            itemBuilder: (context, index) => ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Stack(
                fit: StackFit.expand,
                children: [
                  Image.memory(images[index].bytes, fit: BoxFit.cover),
                  Positioned(
                    right: 4,
                    top: 4,
                    child: IconButton.filled(
                      visualDensity: VisualDensity.compact,
                      onPressed: () => onRemove(index),
                      icon: const Icon(Icons.close_rounded, size: 17),
                      style: IconButton.styleFrom(
                        backgroundColor: Colors.white,
                        foregroundColor: AppColors.text,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: onGallery,
                icon: const Icon(Icons.photo_library_rounded),
                label: const Text('Gallery'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: onCamera,
                icon: const Icon(Icons.camera_alt_rounded),
                label: const Text('Camera'),
              ),
            ),
          ],
        ),
      ],
    ),
  );
}

class _CaptureTips extends StatelessWidget {
  const _CaptureTips();
  @override
  Widget build(BuildContext context) => const Row(
    children: [
      Expanded(
        child: _Tip(
          icon: Icons.center_focus_strong_rounded,
          text: 'Fill the frame',
        ),
      ),
      SizedBox(width: 8),
      Expanded(
        child: _Tip(icon: Icons.wb_sunny_outlined, text: 'Bright light'),
      ),
      SizedBox(width: 8),
      Expanded(
        child: _Tip(icon: Icons.filter_5_rounded, text: 'Use 3–5 angles'),
      ),
    ],
  );
}

class _Tip extends StatelessWidget {
  const _Tip({required this.icon, required this.text});
  final IconData icon;
  final String text;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 6),
    decoration: BoxDecoration(
      color: const Color(0xFFF3F5F2),
      borderRadius: BorderRadius.circular(12),
    ),
    child: Column(
      children: [
        Icon(icon, size: 19, color: AppColors.primary),
        const SizedBox(height: 4),
        Text(
          text,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
        ),
      ],
    ),
  );
}

class _PredictionCard extends StatelessWidget {
  const _PredictionCard({required this.result});
  final PlantPrediction result;
  @override
  Widget build(BuildContext context) {
    final confidence = (result.confidencePercent / 100).clamp(0.0, 1.0);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xFF173D2B),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'AI IDENTIFICATION',
                style: TextStyle(
                  color: Color(0xFFA8D9B8),
                  fontSize: 12,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                result.benefits.commonName,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 25,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                result.benefits.scientificName,
                style: const TextStyle(
                  color: Color(0xFFD6E5DA),
                  fontStyle: FontStyle.italic,
                ),
              ),
              const SizedBox(height: 16),
              LinearProgressIndicator(
                value: confidence,
                minHeight: 9,
                borderRadius: BorderRadius.circular(8),
                color: AppColors.primary,
                backgroundColor: Colors.white24,
              ),
              const SizedBox(height: 8),
              Text(
                '${result.confidencePercent.toStringAsFixed(1)}% confidence',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
        if (result.warning != null) ...[
          const SizedBox(height: 12),
          _Notice(
            text: result.warning!,
            color: const Color(0xFFFFF3D9),
            icon: Icons.info_outline_rounded,
          ),
        ],
        const SizedBox(height: 18),
        _InfoList(
          title: 'Traditional uses',
          icon: Icons.local_florist_rounded,
          items: result.benefits.traditionalUses,
        ),
        const SizedBox(height: 12),
        _InfoList(
          title: 'Preparation notes',
          icon: Icons.science_outlined,
          items: result.benefits.preparationNotes,
        ),
        const SizedBox(height: 12),
        _Notice(
          text: 'Safety: ${result.benefits.safetyWarning}',
          color: const Color(0xFFFFEBD5),
          icon: Icons.health_and_safety_outlined,
        ),
        const SizedBox(height: 10),
        _Notice(
          text: result.benefits.medicalDisclaimer,
          color: const Color(0xFFEAF1FF),
          icon: Icons.medical_information_outlined,
        ),
        if (result.topPredictions.length > 1) ...[
          const SizedBox(height: 18),
          const Text(
            'Other possible matches',
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 8),
          ...result.topPredictions
              .skip(1)
              .take(4)
              .map(
                (item) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: Row(
                    children: [
                      Expanded(child: Text(item.plant.replaceAll('_', ' '))),
                      Text(
                        '${item.confidencePercent.toStringAsFixed(1)}%',
                        style: const TextStyle(fontWeight: FontWeight.w800),
                      ),
                    ],
                  ),
                ),
              ),
        ],
      ],
    );
  }
}

class _InfoList extends StatelessWidget {
  const _InfoList({
    required this.title,
    required this.icon,
    required this.items,
  });
  final String title;
  final IconData icon;
  final List<String> items;
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: AppColors.border),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, color: AppColors.primary, size: 20),
            const SizedBox(width: 8),
            Text(
              title,
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16),
            ),
          ],
        ),
        const SizedBox(height: 9),
        ...items.map(
          (item) => Padding(
            padding: const EdgeInsets.only(bottom: 7),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '•  ',
                  style: TextStyle(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                Expanded(child: Text(item)),
              ],
            ),
          ),
        ),
      ],
    ),
  );
}

class _Notice extends StatelessWidget {
  const _Notice({required this.text, required this.color, required this.icon});
  final String text;
  final Color color;
  final IconData icon;
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(13),
    decoration: BoxDecoration(
      color: color,
      borderRadius: BorderRadius.circular(14),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 20),
        const SizedBox(width: 9),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
      ],
    ),
  );
}
