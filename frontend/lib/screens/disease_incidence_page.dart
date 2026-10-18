import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import '../models/disease_incidence_assessment.dart';
import '../services/plant_api.dart';
import '../theme/app_colors.dart';

class DiseaseIncidencePage extends StatefulWidget {
  const DiseaseIncidencePage({super.key, required this.initialImage});

  final XFile initialImage;

  @override
  State<DiseaseIncidencePage> createState() => _DiseaseIncidencePageState();
}

class _DiseaseIncidencePageState extends State<DiseaseIncidencePage> {
  static const _maxSamples = 25;
  final _picker = ImagePicker();
  final _api = PlantApi();
  final List<XFile> _images = [];
  final List<Uint8List> _previews = [];
  final List<String?> _regions = [];
  DiseaseIncidenceAssessment? _result;
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _addImages([widget.initialImage], initial: true);
  }

  Future<void> _addImages(List<XFile> files, {bool initial = false}) async {
    final remaining = _maxSamples - _images.length;
    final accepted = files.take(remaining).toList();
    final bytes = await Future.wait(accepted.map((file) => file.readAsBytes()));
    if (!mounted) return;
    setState(() {
      _images.addAll(accepted);
      _previews.addAll(bytes);
      _regions.addAll(List<String?>.filled(accepted.length, null));
      _result = null;
      _error = null;
    });
    if (!initial && accepted.length < files.length) {
      _message('Only $_maxSamples total samples can be assessed.');
    }
  }

  Future<void> _camera() async {
    if (_images.length >= _maxSamples)
      return _message('The 25-sample limit is reached.');
    final file = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 75,
      maxWidth: 1600,
      preferredCameraDevice: CameraDevice.rear,
    );
    if (file != null) await _addImages([file]);
  }

  Future<void> _gallery() async {
    final remaining = _maxSamples - _images.length;
    if (remaining <= 0) return _message('The 25-sample limit is reached.');
    final files = await _picker.pickMultiImage(
      imageQuality: 75,
      maxWidth: 1600,
      limit: remaining,
    );
    if (files.isNotEmpty) await _addImages(files);
  }

  void _remove(int index) {
    if (index == 0)
      return _message('The initial diagnosed leaf must remain sample 1.');
    setState(() {
      _images.removeAt(index);
      _previews.removeAt(index);
      _regions.removeAt(index);
      _result = null;
    });
  }

  Future<void> _assess() async {
    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });
    try {
      final result = await _api.assessDiseaseIncidence(_images, _regions);
      if (mounted) setState(() => _result = result);
    } on PlantApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _message(String message) => ScaffoldMessenger.of(
    context,
  ).showSnackBar(SnackBar(content: Text(message)));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Assess Condition Across Plant')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text(
            'Collect distinct leaves from the same plant',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          const Text(
            'Include upper, middle, and lower portions where practical. You can run the assessment with fewer than 25 leaves, but small samples are less reliable.',
            style: TextStyle(color: AppColors.muted, height: 1.4),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _loading ? null : _camera,
                  icon: const Icon(Icons.camera_alt_outlined),
                  label: const Text('Camera'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _loading ? null : _gallery,
                  icon: const Icon(Icons.photo_library_outlined),
                  label: const Text('Gallery'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            '${_images.length} of $_maxSamples total leaf samples',
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 12),
          ...List.generate(_images.length, _sampleTile),
          const SizedBox(height: 8),
          FilledButton.icon(
            onPressed: _loading || _images.isEmpty ? null : _assess,
            icon: _loading
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.analytics_outlined),
            label: Text(
              _loading ? 'Assessing each leaf…' : 'Run Plant Assessment',
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 16),
            _Notice(text: _error!, color: AppColors.danger),
            TextButton.icon(
              onPressed: _loading ? null : _assess,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
          if (_result != null) ...[
            const SizedBox(height: 22),
            _AssessmentResults(result: _result!),
          ],
        ],
      ),
    );
  }

  Widget _sampleTile(int index) {
    const regions = <String>['Upper', 'Middle', 'Lower', 'Other / unsure'];
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.memory(
                _previews[index],
                width: 64,
                height: 64,
                fit: BoxFit.cover,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    index == 0
                        ? 'Sample 1 · Initial leaf'
                        : 'Sample ${index + 1}',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  DropdownButton<String>(
                    isExpanded: true,
                    hint: const Text('Plant region (optional)'),
                    value: _regions[index],
                    items: regions
                        .map(
                          (value) => DropdownMenuItem(
                            value: value,
                            child: Text(value),
                          ),
                        )
                        .toList(),
                    onChanged: _loading
                        ? null
                        : (value) => setState(() => _regions[index] = value),
                  ),
                ],
              ),
            ),
            if (index > 0)
              IconButton(
                onPressed: _loading ? null : () => _remove(index),
                icon: const Icon(Icons.close),
              ),
          ],
        ),
      ),
    );
  }
}

class _AssessmentResults extends StatelessWidget {
  const _AssessmentResults({required this.result});
  final DiseaseIncidenceAssessment result;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '${result.species ?? 'Plant'}: Multi-Sample Plant Condition Assessment',
          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 10),
        Text(
          'Accepted samples: ${result.totalAccepted}/${result.totalSubmitted}',
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        if (result.warnings.isNotEmpty) ...[
          const SizedBox(height: 10),
          ...result.warnings.map(
            (warning) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: _Notice(text: warning, color: Colors.orange.shade800),
            ),
          ),
        ],
        const SizedBox(height: 10),
        ...List.generate(
          result.conditions.length,
          (index) => _ConditionCard(
            condition: result.conditions[index],
            primary: index == 0,
          ),
        ),
        Card(
          child: ListTile(
            leading: const Icon(Icons.eco_outlined, color: AppColors.primary),
            title: const Text('Healthy predictions'),
            subtitle: Text(
              '${result.healthyCount}/${result.totalAccepted} leaves · ${(result.healthyPercentage ?? 0).toStringAsFixed(1)}%',
            ),
          ),
        ),
        const SizedBox(height: 10),
        ExpansionTile(
          title: Text('Per-image results (${result.samples.length})'),
          children: result.samples
              .map(
                (sample) => ListTile(
                  leading: Icon(
                    sample.included
                        ? Icons.check_circle_outline
                        : Icons.cancel_outlined,
                    color: sample.included
                        ? AppColors.primary
                        : AppColors.danger,
                  ),
                  title: Text(
                    'Sample ${sample.index + 1}: ${sample.condition ?? sample.reason?.replaceAll('_', ' ') ?? 'Unavailable'}',
                  ),
                  subtitle: Text(
                    [
                      if (sample.region != null) sample.region!,
                      if (sample.confidence != null)
                        '${(sample.confidence! * 100).toStringAsFixed(1)}% confidence',
                      sample.included
                          ? 'Included'
                          : 'Excluded from denominator',
                    ].join(' · '),
                  ),
                ),
              )
              .toList(),
        ),
        const SizedBox(height: 12),
        const _Notice(
          text:
              'This assessment estimates condition occurrence among the submitted leaf samples. It does not directly measure whole-plant disease severity, confirm the pathogen, or certify medicinal safety.',
          color: AppColors.muted,
        ),
      ],
    );
  }
}

class _ConditionCard extends StatelessWidget {
  const _ConditionCard({required this.condition, required this.primary});
  final IncidenceCondition condition;
  final bool primary;

  @override
  Widget build(BuildContext context) {
    final progress = (condition.percentage / 100).clamp(0.0, 1.0);
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              primary
                  ? 'Primary Condition Under Verification'
                  : 'Additional Observed Condition',
              style: const TextStyle(
                color: AppColors.muted,
                fontWeight: FontWeight.w700,
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              condition.name,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
            ),
            Text(
              '${condition.matchingCount}/${condition.acceptedCount} leaves · ${condition.percentage.toStringAsFixed(1)}% · ${condition.level}',
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(value: progress),
            const SizedBox(height: 12),
            Text('Category: ${condition.category}'),
            if (condition.ruleAvailability != 'available')
              const _Notice(
                text:
                    'Condition-specific incidence rules are unavailable; expert verification is recommended.',
                color: AppColors.danger,
              ),
            _label('Interpretation', condition.interpretation),
            _label('Verification', condition.verification),
            _label('Suggested care', condition.care),
            _label('Follow-up', condition.followUp),
            _label('Medicinal harvest caution', condition.harvestCaution),
            if (condition.references.isNotEmpty)
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: Text(
                  'Scientific references (${condition.references.length})',
                ),
                children: condition.references
                    .map(
                      (reference) => ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(
                          reference.title.isEmpty
                              ? reference.id
                              : reference.title,
                        ),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (reference.publisher.isNotEmpty)
                              Text(reference.publisher),
                            if (reference.url.isNotEmpty)
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.center,
                                children: [
                                  Expanded(
                                    child: SelectableText(reference.url),
                                  ),
                                  IconButton(
                                    tooltip: 'Copy reference link',
                                    visualDensity: VisualDensity.compact,
                                    onPressed: () {
                                      Clipboard.setData(
                                        ClipboardData(text: reference.url),
                                      );
                                      final messenger = ScaffoldMessenger.of(
                                        context,
                                      );
                                      messenger
                                        ..hideCurrentSnackBar()
                                        ..showSnackBar(
                                          const SnackBar(
                                            content: Text(
                                              'Reference link copied',
                                            ),
                                          ),
                                        );
                                    },
                                    icon: const Icon(Icons.copy_rounded),
                                  ),
                                ],
                              ),
                          ],
                        ),
                      ),
                    )
                    .toList(),
              ),
          ],
        ),
      ),
    );
  }

  Widget _label(String label, String text) => text.isEmpty
      ? const SizedBox.shrink()
      : Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Text.rich(
            TextSpan(
              children: [
                TextSpan(
                  text: '$label: ',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                TextSpan(text: text),
              ],
            ),
            style: const TextStyle(height: 1.35),
          ),
        );
}

class _Notice extends StatelessWidget {
  const _Notice({required this.text, required this.color});
  final String text;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    margin: const EdgeInsets.only(top: 6),
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(10),
      border: Border.all(color: color.withValues(alpha: 0.25)),
    ),
    child: Text(text, style: TextStyle(color: color, height: 1.35)),
  );
}
