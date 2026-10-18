import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../services/plant_api.dart';
import '../theme/app_colors.dart';

class AutoHealthScanPage extends StatefulWidget {
  const AutoHealthScanPage({super.key});
  @override
  State<AutoHealthScanPage> createState() => _AutoHealthScanPageState();
}

class _AutoHealthScanPageState extends State<AutoHealthScanPage>
    with WidgetsBindingObserver {
  final _api = PlantApi();
  CameraController? _controller;
  Timer? _timer;
  PlantHealthAssessment? _result;
  String? _candidateStatus;
  String? _error;
  int _stableFrames = 0;
  bool _busy = false;
  bool _paused = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initialize();
  }

  Future<void> _initialize() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty)
        throw CameraException('noCamera', 'No camera found.');
      final back = cameras.where(
        (item) => item.lensDirection == CameraLensDirection.back,
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
        const Duration(milliseconds: 1600),
        (_) => _analyze(),
      );
      _analyze();
    } on CameraException catch (error) {
      if (mounted) setState(() => _error = error.description ?? error.code);
    }
  }

  Future<void> _analyze() async {
    final controller = _controller;
    if (_paused ||
        _busy ||
        controller == null ||
        !controller.value.isInitialized)
      return;
    _busy = true;
    try {
      final frame = await controller.takePicture();
      final assessment = await _api.assessHealth(frame);
      final usable = assessment.status != 'inconclusive';
      if (!usable) {
        _candidateStatus = null;
        _stableFrames = 0;
      } else if (_candidateStatus == assessment.status) {
        _stableFrames++;
      } else {
        _candidateStatus = assessment.status;
        _stableFrames = 1;
      }
      if (mounted) {
        setState(() {
          _result = _stableFrames >= 2 ? assessment : null;
          _error = assessment.captureWarnings.isEmpty
              ? null
              : assessment.captureWarnings.first;
        });
      }
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      _busy = false;
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _paused = state != AppLifecycleState.resumed;
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
        title: const Text('Automatic Health Scan'),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
      ),
      body: controller == null || !controller.value.isInitialized
          ? Center(
              child: _error == null
                  ? const CircularProgressIndicator()
                  : Text(_error!, style: const TextStyle(color: Colors.white)),
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
                          Center(
                            child: Container(
                              width: 260,
                              height: 180,
                              decoration: BoxDecoration(
                                border: Border.all(
                                  color: AppColors.primary,
                                  width: 3,
                                ),
                                borderRadius: BorderRadius.circular(24),
                              ),
                            ),
                          ),
                          if (_busy)
                            const Positioned(
                              top: 12,
                              right: 12,
                              child: CircularProgressIndicator(
                                color: Colors.white,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(18),
                  color: const Color(0xFF102A1E),
                  child: Column(
                    children: [
                      Text(
                        _result?.label ?? 'Center one leaf and hold still',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 5),
                      Text(
                        _result == null
                            ? (_error ??
                                  'Waiting for two clear, matching assessments…')
                            : '${_result!.confidencePercent.toStringAsFixed(1)}% screening confidence',
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Color(0xFFA8D9B8)),
                      ),
                      const SizedBox(height: 12),
                      FilledButton.icon(
                        onPressed: () => setState(() {
                          _paused = !_paused;
                          if (!_paused) _analyze();
                        }),
                        icon: Icon(
                          _paused
                              ? Icons.play_arrow_rounded
                              : Icons.pause_rounded,
                        ),
                        label: Text(_paused ? 'Resume' : 'Pause'),
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }
}
