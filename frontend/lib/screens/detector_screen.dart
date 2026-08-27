import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../models/prediction_result.dart';
import '../services/herb_api.dart';

class DetectorScreen extends StatefulWidget {
  const DetectorScreen({super.key});

  @override
  State<DetectorScreen> createState() => _DetectorScreenState();
}

class _DetectorScreenState extends State<DetectorScreen> {
  final ImagePicker _picker = ImagePicker();
  final HerbApi _api = HerbApi();
  final List<_PickedImage> _images = [];

  PredictionResult? _result;
  bool _isLoading = false;
  bool _isVerifying = false;
  VerificationRequest? _verification;
  String? _error;
  int _requestId = 0;

  Future<void> _pickImages() async {
    final selected = await _picker.pickMultiImage(imageQuality: 88);
    if (selected.isEmpty) return;

    final previews = <_PickedImage>[];
    for (final image in selected.take(5)) {
      previews.add(_PickedImage(file: image, bytes: await image.readAsBytes()));
    }

    setState(() {
      _images
        ..clear()
        ..addAll(previews);
      _result = null;
      _verification = null;
      _error = null;
    });

    await _detectPlant();
  }

  Future<void> _takePhoto() async {
    final photo = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 88,
    );
    if (photo == null) return;

    final preview = _PickedImage(file: photo, bytes: await photo.readAsBytes());

    setState(() {
      if (_images.length == 5) {
        _images.removeAt(0);
      }
      _images.add(preview);
      _result = null;
      _verification = null;
      _error = null;
    });

    await _detectPlant();
  }

  Future<void> _detectPlant() async {
    if (_images.isEmpty) {
      setState(() => _error = 'Add at least one clear leaf or seed image.');
      return;
    }

    final requestId = ++_requestId;
    setState(() {
      _isLoading = true;
      _error = null;
      _result = null;
      _verification = null;
    });

    try {
      final result = await _api.predict(
        _images.map((image) => image.file).toList(),
      );
      if (mounted && requestId == _requestId) {
        setState(() => _result = result);
      }
    } catch (error) {
      if (mounted && requestId == _requestId) {
        setState(() => _error = error.toString());
      }
    } finally {
      if (mounted && requestId == _requestId) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _requestExpertReview() async {
    final result = _result;
    if (result == null || _images.isEmpty) return;
    var consent = false;
    final submit = await showDialog<bool>(context: context, builder: (context) => StatefulBuilder(builder: (context, setDialogState) => AlertDialog(
      title: const Text('Request expert verification'),
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        const Text('Your photos will be re-encoded to remove location and device metadata before a botanist or Ayurvedic expert reviews them.'),
        const SizedBox(height: 12),
        CheckboxListTile(contentPadding: EdgeInsets.zero, value: consent, onChanged: (value) => setDialogState(() => consent = value ?? false), title: const Text('Help improve future models'), subtitle: const Text('Allow verified images to be used for model training. Optional.')),
      ]),
      actions: [TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')), FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Submit securely'))],
    )));
    if (submit != true || !mounted) return;
    setState(() { _isVerifying = true; _error = null; });
    try {
      final value = await _api.requestVerification(images: _images.map((item) => item.file).toList(), prediction: result, trainingConsent: consent);
      if (mounted) setState(() => _verification = value);
    } catch (error) { if (mounted) setState(() => _error = error.toString()); }
    finally { if (mounted) setState(() => _isVerifying = false); }
  }

  Future<void> _refreshExpertReview() async {
    if (_verification == null) return;
    setState(() => _isVerifying = true);
    try {
      final value = await _api.getVerification(_verification!.id);
      if (mounted) setState(() => _verification = value);
    } catch (error) { if (mounted) setState(() => _error = error.toString()); }
    finally { if (mounted) setState(() => _isVerifying = false); }
  }

  void _removeImage(int index) {
    _requestId++;
    setState(() {
      _images.removeAt(index);
      _isLoading = false;
      _result = null;
      _error = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final isWide = width >= 900;

    return Scaffold(
      backgroundColor: const Color(0xFFF5F8F0),
      body: SafeArea(
        child: ListView(
          padding: EdgeInsets.symmetric(
            horizontal: width < 640 ? 16 : 32,
            vertical: 24,
          ),
          children: [
            const _Header(),
            const SizedBox(height: 24),
            if (isWide)
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(flex: 6, child: uploadPanel),
                  const SizedBox(width: 20),
                  Expanded(flex: 4, child: insightPanel),
                ],
              )
            else
              Column(
                children: [
                  uploadPanel,
                  const SizedBox(height: 20),
                  insightPanel,
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget get uploadPanel {
    return _UploadPanel(
      images: _images,
      isLoading: _isLoading,
      onPickImages: _pickImages,
      onTakePhoto: _takePhoto,
      onRemove: _removeImage,
      onDetect: _detectPlant,
    );
  }

  Widget get insightPanel {
    final scheme = Theme.of(context).colorScheme;

    return _InsightPanel(
      result: _result,
      error: _error,
      errorColor: scheme.errorContainer,
      errorTextColor: scheme.onErrorContainer,
      verification: _verification,
      isVerifying: _isVerifying,
      onRequestVerification: _requestExpertReview,
      onRefreshVerification: _refreshExpertReview,
    );
  }
}

class _PickedImage {
  const _PickedImage({required this.file, required this.bytes});

  final XFile file;
  final Uint8List bytes;
}

class _Header extends StatelessWidget {
  const _Header();

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Row(
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: const Color(0xFF173D2B),
            borderRadius: BorderRadius.circular(8),
            boxShadow: const [
              BoxShadow(
                color: Color(0x1F173D2B),
                blurRadius: 18,
                offset: Offset(0, 10),
              ),
            ],
          ),
          child: const Icon(Icons.eco_rounded, color: Color(0xFFEAF6D5)),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Herbal Plant Detector',
                style: textTheme.headlineSmall?.copyWith(
                  color: const Color(0xFF15251C),
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                'Analyze up to 5 leaf or seed photos with confidence scoring.',
                style: textTheme.bodyMedium?.copyWith(
                  color: const Color(0xFF607066),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _UploadPanel extends StatelessWidget {
  const _UploadPanel({
    required this.images,
    required this.isLoading,
    required this.onPickImages,
    required this.onTakePhoto,
    required this.onRemove,
    required this.onDetect,
  });

  final List<_PickedImage> images;
  final bool isLoading;
  final VoidCallback onPickImages;
  final VoidCallback onTakePhoto;
  final ValueChanged<int> onRemove;
  final VoidCallback onDetect;

  @override
  Widget build(BuildContext context) {
    return _Surface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionTitle(
            title: 'Image Set',
            subtitle: 'Use close-up leaf photos for the most reliable match.',
          ),
          const SizedBox(height: 14),
          const _CaptureGuide(),
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: isLoading ? null : onPickImages,
                  icon: const Icon(Icons.photo_library_rounded),
                  label: const Text('Gallery'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: isLoading ? null : onTakePhoto,
                  icon: const Icon(Icons.photo_camera_rounded),
                  label: const Text('Camera'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          _ImageGrid(images: images, onRemove: onRemove),
          const SizedBox(height: 18),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: FilledButton.icon(
              onPressed: isLoading ? null : onDetect,
              icon: isLoading
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.spa_rounded),
              label: Text(isLoading ? 'Detecting...' : 'Detect plant'),
            ),
          ),
        ],
      ),
    );
  }
}

class _CaptureGuide extends StatelessWidget {
  const _CaptureGuide();

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: [
        _CaptureTip(
          icon: Icons.center_focus_strong_rounded,
          text: 'Keep one leaf centered and fill most of the frame.',
        ),
        SizedBox(height: 8),
        _CaptureTip(
          icon: Icons.wb_sunny_rounded,
          text: 'Use bright natural light and avoid heavy shadows.',
        ),
        SizedBox(height: 8),
        _CaptureTip(
          icon: Icons.filter_5_rounded,
          text:
              'Add 3 to 5 photos from different angles for better confidence.',
        ),
      ],
    );
  }
}

class _CaptureTip extends StatelessWidget {
  const _CaptureTip({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 18, color: const Color(0xFF2F7347)),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: const Color(0xFF526259)),
          ),
        ),
      ],
    );
  }
}

class _ImageGrid extends StatelessWidget {
  const _ImageGrid({required this.images, required this.onRemove});

  final List<_PickedImage> images;
  final ValueChanged<int> onRemove;

  @override
  Widget build(BuildContext context) {
    if (images.isEmpty) {
      return Container(
        height: 280,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: const Color(0xFFEFF5EA),
          border: Border.all(color: const Color(0xFFD9E3D4)),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 58,
              height: 58,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(
                Icons.add_photo_alternate_rounded,
                color: Color(0xFF2F7347),
                size: 30,
              ),
            ),
            const SizedBox(height: 14),
            Text(
              'No images selected',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(
              'Add 1 to 5 leaf or seed images.',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: const Color(0xFF718075)),
            ),
          ],
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth < 520 ? 2 : 3;

        return GridView.builder(
          itemCount: images.length,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
          ),
          itemBuilder: (context, index) {
            return ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Stack(
                fit: StackFit.expand,
                children: [
                  Image.memory(images[index].bytes, fit: BoxFit.cover),
                  DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          Colors.black.withValues(alpha: 0.38),
                          Colors.transparent,
                        ],
                      ),
                    ),
                  ),
                  Positioned(
                    top: 6,
                    right: 6,
                    child: IconButton.filled(
                      visualDensity: VisualDensity.compact,
                      style: IconButton.styleFrom(
                        backgroundColor: Colors.white,
                        foregroundColor: const Color(0xFF173D2B),
                      ),
                      onPressed: () => onRemove(index),
                      icon: const Icon(Icons.close_rounded, size: 18),
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }
}

class _InsightPanel extends StatelessWidget {
  const _InsightPanel({
    required this.result,
    required this.error,
    required this.errorColor,
    required this.errorTextColor,
    required this.verification,
    required this.isVerifying,
    required this.onRequestVerification,
    required this.onRefreshVerification,
  });

  final PredictionResult? result;
  final String? error;
  final Color errorColor;
  final Color errorTextColor;
  final VerificationRequest? verification;
  final bool isVerifying;
  final VoidCallback onRequestVerification;
  final VoidCallback onRefreshVerification;

  @override
  Widget build(BuildContext context) {
    return _Surface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionTitle(
            title: 'Result',
            subtitle:
                'AI-based Ayurvedic benefits, prediction confidence, and safety notes appear here.',
          ),
          if (error != null) ...[
            const SizedBox(height: 16),
            _MessageBox(
              icon: Icons.error_outline_rounded,
              color: errorColor,
              textColor: errorTextColor,
              text: error!,
            ),
          ],
          if (result == null && error == null) const _EmptyResult(),
          if (result != null) ...[
            const SizedBox(height: 18),
            _ResultPanel(result: result!, verification: verification, isVerifying: isVerifying, onRequestVerification: onRequestVerification, onRefreshVerification: onRefreshVerification),
          ],
        ],
      ),
    );
  }
}

class _EmptyResult extends StatelessWidget {
  const _EmptyResult();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 18),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF1C3327),
        borderRadius: BorderRadius.circular(8),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.analytics_rounded, color: Color(0xFFEAF6D5)),
          SizedBox(height: 14),
          Text(
            'Ready for analysis',
            style: TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w800,
            ),
          ),
          SizedBox(height: 6),
          Text(
            'Upload your images, then run detection to view the best match, confidence, and educational herbal notes.',
            style: TextStyle(color: Color(0xFFD5E4D8), height: 1.4),
          ),
        ],
      ),
    );
  }
}

class _ResultPanel extends StatelessWidget {
  const _ResultPanel({required this.result, required this.verification, required this.isVerifying, required this.onRequestVerification, required this.onRefreshVerification});

  final PredictionResult result;
  final VerificationRequest? verification;
  final bool isVerifying;
  final VoidCallback onRequestVerification;
  final VoidCallback onRefreshVerification;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: const Color(0xFF173D2B),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _StatusBadge(text: verification?.identificationLabel ?? 'AI identified', verified: verification?.isVerified ?? false),
              const SizedBox(height: 12),
              Text(
                verification?.expertIdentification ?? result.benefits.commonName,
                style: textTheme.headlineSmall?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                result.benefits.scientificName,
                style: textTheme.bodyMedium?.copyWith(
                  color: const Color(0xFFD5E4D8),
                  fontStyle: FontStyle.italic,
                ),
              ),
              const SizedBox(height: 16),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  minHeight: 10,
                  value: result.confidencePercent / 100,
                  color: const Color(0xFFB9E769),
                  backgroundColor: Colors.white.withValues(alpha: 0.16),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                '${result.confidencePercent.toStringAsFixed(2)}% confidence',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
        if (result.warning != null || verification != null) ...[
          const SizedBox(height: 12),
          _ExpertReviewCard(verification: verification, isLoading: isVerifying, onSubmit: onRequestVerification, onRefresh: onRefreshVerification),
        ],
        if (result.warning != null) ...[
          const SizedBox(height: 12),
          _MessageBox(
            icon: Icons.info_outline_rounded,
            color: scheme.tertiaryContainer,
            textColor: scheme.onTertiaryContainer,
            text: result.warning!,
          ),
        ],
        if (result.imageQuality.isNotEmpty) ...[
          const SizedBox(height: 16),
          Text(
            'Image preprocessing',
            style: textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          ...result.imageQuality.map((quality) {
            final details = quality.warnings.isEmpty
                ? quality.foregroundCropped
                      ? 'Foreground found and excess background cropped.'
                      : 'Image quality is suitable; original framing preserved.'
                : quality.warnings.join(' ');
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    quality.warnings.isEmpty
                        ? Icons.auto_fix_high_rounded
                        : Icons.photo_camera_back_rounded,
                    size: 18,
                    color: const Color(0xFF2F7347),
                  ),
                  const SizedBox(width: 8),
                  Expanded(child: Text('${quality.filename}: $details')),
                ],
              ),
            );
          }),
        ],
        const SizedBox(height: 18),
        _InfoSection(
          title: 'Traditional Uses',
          icon: Icons.local_florist_rounded,
          items: result.benefits.traditionalUses,
        ),
        const SizedBox(height: 16),
        _InfoSection(
          title: 'Preparation Notes',
          icon: Icons.science_rounded,
          items: result.benefits.preparationNotes,
        ),
        const SizedBox(height: 12),
        _MessageBox(
          icon: Icons.health_and_safety_rounded,
          color: const Color(0xFFFFF0D9),
          textColor: const Color(0xFF60410D),
          text: 'Safety Warning: ${result.benefits.safetyWarning}',
        ),
        const SizedBox(height: 12),
        _MessageBox(
          icon: Icons.medical_information_rounded,
          color: const Color(0xFFEAF0FF),
          textColor: const Color(0xFF1E356B),
          text: 'Not Medical Advice: ${result.benefits.medicalDisclaimer}',
        ),
        const SizedBox(height: 18),
        Text(
          'Top matches',
          style: textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 8),
        ...result.topPredictions.map(
          (item) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Row(
              children: [
                Expanded(child: Text(item.plant.replaceAll('_', ' '))),
                const SizedBox(width: 12),
                Text(
                  '${item.confidencePercent.toStringAsFixed(1)}%',
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _InfoSection extends StatelessWidget {
  const _InfoSection({
    required this.title,
    required this.icon,
    required this.items,
  });

  final String title;
  final IconData icon;
  final List<String> items;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 20, color: const Color(0xFF2F7347)),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                title,
                style: textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ...items.map(
          (item) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.check_circle_rounded,
                  size: 18,
                  color: Color(0xFF2F7347),
                ),
                const SizedBox(width: 8),
                Expanded(child: Text(item)),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.text, required this.verified});
  final String text;
  final bool verified;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
    decoration: BoxDecoration(
      color: verified ? const Color(0xFFB9E769) : Colors.white.withValues(alpha: 0.16),
      borderRadius: BorderRadius.circular(20),
    ),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Icon(verified ? Icons.verified_rounded : Icons.auto_awesome_rounded, size: 16, color: verified ? const Color(0xFF173D2B) : Colors.white),
      const SizedBox(width: 6),
      Text(text, style: TextStyle(color: verified ? const Color(0xFF173D2B) : Colors.white, fontWeight: FontWeight.w800)),
    ]),
  );
}

class _ExpertReviewCard extends StatelessWidget {
  const _ExpertReviewCard({required this.verification, required this.isLoading, required this.onSubmit, required this.onRefresh});
  final VerificationRequest? verification;
  final bool isLoading;
  final VoidCallback onSubmit;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final verified = verification?.isVerified ?? false;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: const Color(0xFFEFF5EA), border: Border.all(color: const Color(0xFFD4E2CF)), borderRadius: BorderRadius.circular(8)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(verified ? 'Identification verified' : verification == null ? 'Low confidence? Ask an expert' : 'Expert review pending', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
        const SizedBox(height: 6),
        Text(verified
          ? '${verification!.expertIdentification}${verification!.reviewerName == null ? '' : ' — reviewed by ${verification!.reviewerName}'}'
          : verification == null
            ? 'Submit these photos for review by a botanist or Ayurvedic expert. Location metadata is removed first.'
            : 'Your private image set is in the review queue. Reference: ${verification!.id.substring(0, 8)}'),
        if (verified && (verification!.expertNotes?.isNotEmpty ?? false)) ...[const SizedBox(height: 6), Text(verification!.expertNotes!)],
        const SizedBox(height: 10),
        Align(alignment: Alignment.centerRight, child: FilledButton.tonalIcon(
          onPressed: isLoading ? null : verification == null ? onSubmit : onRefresh,
          icon: isLoading ? const SizedBox.square(dimension: 16, child: CircularProgressIndicator(strokeWidth: 2)) : Icon(verification == null ? Icons.verified_user_rounded : Icons.refresh_rounded),
          label: Text(isLoading ? 'Please wait...' : verification == null ? 'Request verification' : 'Check status'),
        )),
      ]),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            color: const Color(0xFF15251C),
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          subtitle,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: const Color(0xFF66766B)),
        ),
      ],
    );
  }
}

class _Surface extends StatelessWidget {
  const _Surface({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: const Color(0xFFE1E9DD)),
        borderRadius: BorderRadius.circular(8),
        boxShadow: const [
          BoxShadow(
            color: Color(0x140B2618),
            blurRadius: 28,
            offset: Offset(0, 14),
          ),
        ],
      ),
      child: child,
    );
  }
}

class _MessageBox extends StatelessWidget {
  const _MessageBox({
    required this.icon,
    required this.color,
    required this.textColor,
    required this.text,
  });

  final IconData icon;
  final Color color;
  final Color textColor;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: textColor),
          const SizedBox(width: 10),
          Expanded(
            child: Text(text, style: TextStyle(color: textColor)),
          ),
        ],
      ),
    );
  }
}
