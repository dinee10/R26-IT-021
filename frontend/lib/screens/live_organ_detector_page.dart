import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../services/plant_api.dart';
import '../theme/app_colors.dart';

class LiveOrganDetectorPage extends StatefulWidget {
  const LiveOrganDetectorPage({super.key});

  @override
  State<LiveOrganDetectorPage> createState() => _LiveOrganDetectorPageState();
}

class _LiveOrganDetectorPageState extends State<LiveOrganDetectorPage>
    with WidgetsBindingObserver {
  final PlantApi _api = PlantApi();
  CameraController? _controller;
  Timer? _timer;
  List<OrganDetection> _detections = const [];
  LivePlantIdentification? _identification;
  String? _candidatePlant;
  int _candidateFrames = 0;
  String? _error;
  bool _sending = false;
  bool _paused = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty)
        throw CameraException('noCamera', 'No camera found.');
      final back = cameras.where(
        (c) => c.lensDirection == CameraLensDirection.back,
      );
      final controller = CameraController(
        back.isNotEmpty ? back.first : cameras.first,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );
      await controller.initialize();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      setState(() => _controller = controller);
      _timer = Timer.periodic(
        const Duration(milliseconds: 1100),
        (_) => _scanFrame(),
      );
      _scanFrame();
    } on CameraException catch (error) {
      if (mounted) setState(() => _error = error.description ?? error.code);
    }
  }

  Future<void> _scanFrame() async {
    final controller = _controller;
    if (_paused ||
        _sending ||
        controller == null ||
        !controller.value.isInitialized)
      return;
    _sending = true;
    try {
      final frame = await controller.takePicture();
      final result = await _api.identifyLive(frame);
      final candidate = result.identification;
      if (candidate == null || candidate.confidencePercent < 60) {
        _candidatePlant = null;
        _candidateFrames = 0;
      } else if (_candidatePlant == candidate.plant) {
        _candidateFrames++;
      } else {
        _candidatePlant = candidate.plant;
        _candidateFrames = 1;
      }
      if (mounted) {
        setState(() {
          _detections = result.detections;
          _identification = _candidateFrames >= 2 ? candidate : null;
          _error = null;
        });
      }
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      _sending = false;
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.inactive ||
        state == AppLifecycleState.paused) {
      _paused = true;
    } else if (state == AppLifecycleState.resumed) {
      _paused = false;
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = _controller;
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('Live leaf, seed & flower scan'),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
      ),
      body: controller == null || !controller.value.isInitialized
          ? Center(
              child: _error == null
                  ? const CircularProgressIndicator()
                  : _ErrorText(_error!),
            )
          : Column(
              children: [
                Expanded(
                  child: Center(
                    child: AspectRatio(
                      aspectRatio: controller.value.aspectRatio,
                      child: Stack(
                        fit: StackFit.expand,
                        children: [
                          CameraPreview(controller),
                          Positioned.fill(
                            child: CustomPaint(
                              painter: _DetectionPainter(_detections),
                            ),
                          ),
                          if (_sending)
                            const Positioned(
                              top: 12,
                              right: 12,
                              child: SizedBox.square(
                                dimension: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  color: const Color(0xFF102A1E),
                  child: Column(
                    children: [
                      Text(
                        _identification != null
                            ? '${_identification!.plant.replaceAll('_', ' ')} — ${_identification!.confidencePercent.toStringAsFixed(1)}%'
                            : _detections.isEmpty
                            ? 'Point the camera at a leaf, seed, or flower'
                            : 'Hold still while the species is confirmed',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      if (_identification != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          '${_identification!.organ} detected at ${_identification!.organConfidencePercent.toStringAsFixed(0)}%',
                          style: const TextStyle(
                            color: Color(0xFFA8D9B8),
                            fontSize: 12,
                          ),
                        ),
                      ],
                      if (_error != null) ...[
                        const SizedBox(height: 8),
                        Text(
                          _error!,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            color: Color(0xFFFFC8BD),
                            fontSize: 12,
                          ),
                        ),
                      ],
                      const SizedBox(height: 10),
                      FilledButton.icon(
                        onPressed: () => setState(() {
                          _paused = !_paused;
                          if (!_paused) _scanFrame();
                        }),
                        icon: Icon(
                          _paused
                              ? Icons.play_arrow_rounded
                              : Icons.pause_rounded,
                        ),
                        label: Text(
                          _paused ? 'Resume scanning' : 'Pause scanning',
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }
}

class _DetectionPainter extends CustomPainter {
  const _DetectionPainter(this.detections);
  final List<OrganDetection> detections;

  @override
  void paint(Canvas canvas, Size size) {
    final border = Paint()
      ..color = AppColors.primary
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;
    final background = Paint()..color = AppColors.primary;
    for (final detection in detections) {
      final rect = Rect.fromLTRB(
        detection.left * size.width,
        detection.top * size.height,
        detection.right * size.width,
        detection.bottom * size.height,
      );
      canvas.drawRect(rect, border);
      final painter = TextPainter(
        text: TextSpan(
          text:
              '${detection.label} ${detection.confidencePercent.toStringAsFixed(0)}%',
          style: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w900,
            fontSize: 12,
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      final labelRect = Rect.fromLTWH(
        rect.left,
        rect.top,
        painter.width + 12,
        painter.height + 6,
      );
      canvas.drawRect(labelRect, background);
      painter.paint(canvas, Offset(rect.left + 6, rect.top + 3));
    }
  }

  @override
  bool shouldRepaint(covariant _DetectionPainter oldDelegate) =>
      oldDelegate.detections != detections;
}

class _ErrorText extends StatelessWidget {
  const _ErrorText(this.message);
  final String message;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(24),
    child: Text(
      message,
      textAlign: TextAlign.center,
      style: const TextStyle(color: Colors.white),
    ),
  );
}
