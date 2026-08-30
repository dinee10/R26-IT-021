import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../services/plant_api.dart';
import '../theme/app_colors.dart';
import 'auto_health_scan_page.dart';

class QualityAssessmentPage extends StatefulWidget {
  const QualityAssessmentPage({super.key});
  @override
  State<QualityAssessmentPage> createState() => _QualityAssessmentPageState();
}

class _QualityAssessmentPageState extends State<QualityAssessmentPage> {
  final _picker = ImagePicker();
  final _api = PlantApi();
  XFile? _image;
  Uint8List? _bytes;
  PlantHealthAssessment? _result;
  String? _error;
  bool _loading = false;

  Future<void> _select(ImageSource source) async {
    final image = await _picker.pickImage(source: source, imageQuality: 90);
    if (image == null) return;
    final bytes = await image.readAsBytes();
    if (!mounted) return;
    setState(() {
      _image = image;
      _bytes = bytes;
      _result = null;
      _error = null;
    });
    await _assess();
  }

  Future<void> _assess() async {
    final image = _image;
    if (image == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await _api.assessHealth(image);
      if (mounted) setState(() => _result = result);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Plant Health Assessment')),
    body: SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(22, 16, 22, 32),
        children: [
          const Text(
            'Check visible leaf condition',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 6),
          const Text(
            'Use one leaf in bright, indirect light. This checks visible colour and image quality; it does not diagnose disease.',
            style: TextStyle(
              color: AppColors.muted,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => const AutoHealthScanPage(),
              ),
            ),
            icon: const Icon(Icons.center_focus_strong_rounded),
            label: const Text('Start automatic live assessment'),
            style: FilledButton.styleFrom(
              minimumSize: const Size.fromHeight(50),
            ),
          ),
          const SizedBox(height: 14),
          Container(
            height: 240,
            clipBehavior: Clip.antiAlias,
            decoration: BoxDecoration(
              color: const Color(0xFFEAFBF0),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.border),
            ),
            child: _bytes == null
                ? const Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.eco_rounded,
                        size: 54,
                        color: AppColors.primary,
                      ),
                      SizedBox(height: 10),
                      Text(
                        'Add a clear leaf photo',
                        style: TextStyle(fontWeight: FontWeight.w900),
                      ),
                    ],
                  )
                : Image.memory(
                    _bytes!,
                    width: double.infinity,
                    fit: BoxFit.cover,
                  ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _loading
                      ? null
                      : () => _select(ImageSource.gallery),
                  icon: const Icon(Icons.photo_library_rounded),
                  label: const Text('Gallery'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton.icon(
                  onPressed: _loading
                      ? null
                      : () => _select(ImageSource.camera),
                  icon: const Icon(Icons.camera_alt_rounded),
                  label: const Text('Camera'),
                ),
              ),
            ],
          ),
          if (_loading) ...[
            const SizedBox(height: 18),
            const Center(child: CircularProgressIndicator()),
          ],
          if (_error != null) ...[
            const SizedBox(height: 16),
            _MessageCard(text: _error!, color: const Color(0xFFFFE8E3)),
          ],
          if (_result != null) ...[
            const SizedBox(height: 20),
            _AssessmentResult(result: _result!),
          ],
        ],
      ),
    ),
  );
}

class _AssessmentResult extends StatelessWidget {
  const _AssessmentResult({required this.result});
  final PlantHealthAssessment result;
  @override
  Widget build(BuildContext context) {
    final color = result.status == 'healthy_looking'
        ? AppColors.primary
        : result.status == 'inconclusive'
        ? const Color(0xFFE99A1E)
        : const Color(0xFFD65C45);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(18),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                result.label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 21,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                '${result.confidencePercent.toStringAsFixed(1)}% screening confidence',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
        if (result.captureWarnings.isNotEmpty) ...[
          const SizedBox(height: 12),
          _MessageCard(
            text: result.captureWarnings.join('\n'),
            color: const Color(0xFFFFF3D9),
          ),
        ],
        if (result.symptoms.isNotEmpty) ...[
          const SizedBox(height: 12),
          _ListCard(title: 'Visible signals', items: result.symptoms),
        ],
        const SizedBox(height: 12),
        _ListCard(
          title: 'Visual measurements',
          items: _metricItems(result.metrics),
        ),
        const SizedBox(height: 12),
        _ListCard(
          title: 'Recommended next steps',
          items: result.recommendations,
        ),
        const SizedBox(height: 12),
        _MessageCard(text: result.disclaimer, color: const Color(0xFFEAF1FF)),
      ],
    );
  }

  static List<String> _metricItems(Map<String, double> metrics) =>
      {
            'Green tissue': metrics['green_percent'],
            'Yellow tissue': metrics['yellow_percent'],
            'Brown tissue': metrics['brown_percent'],
            'Dark tissue': metrics['dark_percent'],
            'Brightness': metrics['brightness'],
          }.entries
          .map(
            (item) => '${item.key}: ${(item.value ?? 0).toStringAsFixed(1)}%',
          )
          .toList();
}

class _ListCard extends StatelessWidget {
  const _ListCard({required this.title, required this.items});
  final String title;
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
        Text(
          title,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900),
        ),
        const SizedBox(height: 8),
        ...items.map(
          (item) => Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Text('•  $item'),
          ),
        ),
      ],
    ),
  );
}

class _MessageCard extends StatelessWidget {
  const _MessageCard({required this.text, required this.color});
  final String text;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: color,
      borderRadius: BorderRadius.circular(14),
    ),
    child: Text(text, style: const TextStyle(fontWeight: FontWeight.w600)),
  );
}
