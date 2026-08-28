import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../services/api_service.dart';
import '../services/weather_service.dart';
import '../theme/app_colors.dart';

class CultivationPage extends StatefulWidget {
  const CultivationPage({super.key});

  @override
  State<CultivationPage> createState() => _CultivationPageState();
}

class _CultivationPageState extends State<CultivationPage> {
  final _formKey = GlobalKey<FormState>();
  final _temperature = TextEditingController();
  final _humidity = TextEditingController();
  final _rainfall = TextEditingController();
  final _budgetAmount = TextEditingController();
  final _weatherService = WeatherService();
  final _apiService = ApiService();
  String? _soilType;
  String? _landSize;
  String _budgetCurrency = 'LKR';
  String? _irrigation;
  String? _sunlight;
  String _growingSeason = _months[DateTime.now().month - 1];
  String? _growingDuration;
  String _weatherStatus = 'Detecting local weather...';
  bool _loadingWeather = true;
  List<PlantRecommendation> _recommendations = const [];
  bool _loadingRecommendations = false;
  String? _recommendationError;

  static const _months = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];

  static const _currencies = ['LKR', 'USD', 'EUR', 'GBP', 'INR', 'AUD', 'CAD', 'JPY'];

  @override
  void initState() {
    super.initState();
    _detectWeather();
  }

  @override
  void dispose() {
    _temperature.dispose();
    _humidity.dispose();
    _rainfall.dispose();
    _budgetAmount.dispose();
    super.dispose();
  }

  Future<void> _detectWeather() async {
    setState(() {
      _loadingWeather = true;
      _weatherStatus = 'Detecting local weather...';
    });
    try {
      final weather = await _weatherService.autoDetectWeather();
      if (!mounted) return;
      _temperature.text = weather.temperature.toStringAsFixed(1);
      _humidity.text = weather.humidity.toStringAsFixed(0);
      _rainfall.text = weather.rainfall.toStringAsFixed(1);
      setState(() {
        _loadingWeather = false;
        _weatherStatus = weather.location == null
            ? 'Weather updated from your current location'
            : 'Weather updated for ${weather.location}';
      });
    } on WeatherException catch (error) {
      if (!mounted) return;
      setState(() {
        _loadingWeather = false;
        _weatherStatus = error.message;
      });
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    final recommendationInput = _recommendationInput;
    setState(() {
      _loadingRecommendations = true;
      _recommendationError = null;
      _recommendations = const [];
    });
    try {
      final recommendations = await _apiService.recommend(recommendationInput);
      if (!mounted) return;
      setState(() {
        _loadingRecommendations = false;
        _recommendations = recommendations.take(5).toList();
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _loadingRecommendations = false;
        _recommendationError = error.message;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loadingRecommendations = false;
        _recommendationError = 'Could not connect to the recommendation service.';
      });
    }
  }

  Map<String, dynamic> get _recommendationInput => {
        'temperature': double.parse(_temperature.text),
        'rainfall': double.parse(_rainfall.text),
        'humidity': double.parse(_humidity.text),
        'soilType': _soilType,
        'growingSpace': _landSize,
        'budgetAmount': int.parse(_budgetAmount.text.replaceAll(',', '')),
        'budgetCurrency': _budgetCurrency,
        'irrigationMethod': _irrigation,
        'sunlight': _sunlight,
        'growingSeason': _growingSeason,
        'growingDuration': _growingDuration,
      };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Cultivation')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
          children: [
            const Text('Plan your crop', style: TextStyle(color: AppColors.text, fontSize: 28, fontWeight: FontWeight.w900)),
            const SizedBox(height: 6),
            const Text('Use current weather and farm details to prepare a recommendation.', style: TextStyle(color: AppColors.muted, fontWeight: FontWeight.w600)),
            const SizedBox(height: 20),
            _WeatherCard(status: _weatherStatus, loading: _loadingWeather, onRefresh: _detectWeather),
            const SizedBox(height: 24),
            const _SectionTitle(title: 'Weather data', icon: Icons.cloud_rounded),
            const SizedBox(height: 12),
            Row(children: [Expanded(child: _numberField(_temperature, 'Temperature', '°C')), const SizedBox(width: 12), Expanded(child: _numberField(_humidity, 'Humidity', '%'))]),
            const SizedBox(height: 12),
            _numberField(_rainfall, 'Rainfall', 'mm'),
            const SizedBox(height: 24),
            const _SectionTitle(title: 'Farm details', icon: Icons.agriculture_rounded),
            const SizedBox(height: 12),
            _dropdown('What type of soil do you have?', _soilType, const [
              'Loamy - soft, balanced soil',
              'Sandy - loose and drains quickly',
              'Clay - heavy and holds water',
              'Silty - smooth and holds moisture',
              'Not sure - I do not know',
            ], (value) => setState(() => _soilType = value)),
            _dropdown('Where will you grow the plant?', _landSize, const [
              'Small pot or container',
              'Small garden',
              'Medium garden',
              'Large garden',
              'Farm or large field',
            ], (value) => setState(() => _landSize = value)),
            const SizedBox(height: 4),
            const Text('How much can you spend on growing this plant?', style: TextStyle(color: AppColors.text, fontSize: 16, fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            const Text('Enter your approximate budget for seeds/plants, soil, fertilizer and other basic gardening supplies.', style: TextStyle(color: AppColors.muted, fontSize: 13, fontWeight: FontWeight.w600)),
            const SizedBox(height: 10),
            LayoutBuilder(builder: (context, constraints) {
              final compact = constraints.maxWidth < 360;
              final currencyField = DropdownButtonFormField<String>(initialValue: _budgetCurrency, items: _currencies.map((currency) => DropdownMenuItem(value: currency, child: Text(currency))).toList(), onChanged: (value) => setState(() => _budgetCurrency = value ?? _budgetCurrency), decoration: const InputDecoration(prefixIcon: Icon(Icons.currency_exchange_rounded)));
              final amountField = TextFormField(controller: _budgetAmount, keyboardType: TextInputType.number, inputFormatters: [FilteringTextInputFormatter.digitsOnly, _ThousandsSeparatorFormatter()], validator: (value) => value == null || value.trim().isEmpty ? 'Required' : null, decoration: const InputDecoration(labelText: 'Budget amount', hintText: 'Example: 5,000', prefixIcon: Icon(Icons.payments_outlined)));
              return compact ? Column(children: [currencyField, const SizedBox(height: 12), amountField]) : Row(children: [SizedBox(width: 96, child: currencyField), const SizedBox(width: 12), Expanded(child: amountField)]);
            }),
            const SizedBox(height: 12),
            _dropdown('How will you provide water?', _irrigation, const ['Rain only', 'Hand watering', 'Drip irrigation', 'Sprinkler', 'Hose', 'Other'], (value) => setState(() => _irrigation = value)),
            _dropdown('How much sunlight does the growing area get?', _sunlight, const ['Low sunlight - less than about 3 hours daily', 'Partial sunlight - about 3 to 6 hours daily', 'Full sunlight - about 6 or more hours daily'], (value) => setState(() => _sunlight = value)),
            _dropdown('When do you plan to plant?', _growingSeason, _months, (value) => setState(() => _growingSeason = value ?? _growingSeason)),
            _dropdown('How long do you want to grow the plant?', _growingDuration, const ['Short - a few weeks to a few months', 'Medium - several months', 'Long - many months or longer'], (value) => setState(() => _growingDuration = value)),
            const Padding(padding: EdgeInsets.only(top: 0, bottom: 4), child: Text('This is how long you are willing to wait before harvesting or seeing the plant mature.', style: TextStyle(color: AppColors.muted, fontSize: 13, fontWeight: FontWeight.w600))),
            const SizedBox(height: 20),
            FilledButton.icon(onPressed: _loadingRecommendations ? null : _submit, icon: _loadingRecommendations ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.eco_rounded), label: Text(_loadingRecommendations ? 'Finding suitable plants...' : 'Get crop recommendation'), style: FilledButton.styleFrom(backgroundColor: AppColors.primary, foregroundColor: Colors.white, minimumSize: const Size.fromHeight(54), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)))),
            if (_recommendationError != null) ...[
              const SizedBox(height: 12),
              Text(_recommendationError!, style: const TextStyle(color: AppColors.danger, fontWeight: FontWeight.w700)),
            ],
            if (_recommendations.isNotEmpty) ...[
              const SizedBox(height: 28),
              const _SectionTitle(title: 'Recommended plants', icon: Icons.local_florist_rounded),
              const SizedBox(height: 12),
              ..._recommendations.asMap().entries.map((entry) => _RecommendationCard(position: entry.key + 1, recommendation: entry.value)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _numberField(TextEditingController controller, String label, String suffix) {
    return TextFormField(controller: controller, readOnly: true, validator: (value) => value == null || value.trim().isEmpty ? 'Detect weather first' : null, decoration: InputDecoration(labelText: label, suffixText: suffix, prefixIcon: const Icon(Icons.cloud_outlined)));
  }

  Widget _dropdown(String label, String? value, List<String> options, ValueChanged<String?> onChanged) {
    return Padding(padding: const EdgeInsets.only(bottom: 12), child: DropdownButtonFormField<String>(initialValue: value, selectedItemBuilder: (context) => options.map((option) => Align(alignment: Alignment.centerLeft, child: Text(option, maxLines: 1, overflow: TextOverflow.ellipsis))).toList(), items: options.map((option) => DropdownMenuItem(value: option, child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 300), child: Text(option, maxLines: 2, overflow: TextOverflow.ellipsis)))).toList(), onChanged: onChanged, validator: (value) => value == null ? 'Required' : null, decoration: InputDecoration(labelText: label, prefixIcon: const Icon(Icons.tune_rounded))));
  }
}

class _ThousandsSeparatorFormatter extends TextInputFormatter {
  const _ThousandsSeparatorFormatter();

  @override
  TextEditingValue formatEditUpdate(TextEditingValue oldValue, TextEditingValue newValue) {
    final digits = newValue.text.replaceAll(',', '');
    if (digits.isEmpty) return newValue.copyWith(text: '');
    final formatted = digits.replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (match) => ',');
    return newValue.copyWith(text: formatted, selection: TextSelection.collapsed(offset: formatted.length));
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, required this.icon});
  final String title;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Row(children: [Icon(icon, color: AppColors.primary, size: 21), const SizedBox(width: 8), Text(title, style: const TextStyle(color: AppColors.text, fontSize: 17, fontWeight: FontWeight.w900))]);
}

class _RecommendationCard extends StatelessWidget {
  const _RecommendationCard({required this.position, required this.recommendation});

  final int position;
  final PlantRecommendation recommendation;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 18,
            backgroundColor: AppColors.primary.withValues(alpha: 0.12),
            child: Text('$position', style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w900)),
          ),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(recommendation.name, style: const TextStyle(color: AppColors.text, fontSize: 16, fontWeight: FontWeight.w800)), const SizedBox(height: 3), Text(recommendation.reason, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: AppColors.muted, fontSize: 12, fontWeight: FontWeight.w600))])),
          const Icon(Icons.eco_rounded, color: AppColors.primary),
        ],
      ),
    );
  }
}

class _WeatherCard extends StatelessWidget {
  const _WeatherCard({required this.status, required this.loading, required this.onRefresh});
  final String status;
  final bool loading;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) => Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: const Color(0xFFEAF6FF), borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFFC7E7F8))), child: Row(children: [const Icon(Icons.location_on_rounded, color: Color(0xFF2385B8), size: 27), const SizedBox(width: 12), Expanded(child: Text(status, style: const TextStyle(color: AppColors.text, fontWeight: FontWeight.w700))), if (loading) const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2)) else IconButton(onPressed: onRefresh, tooltip: 'Refresh weather', icon: const Icon(Icons.refresh_rounded))]));
}
