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
  final _soilPh = TextEditingController();
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
  PlantRecommendation? _bestPlant;
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
    _soilPh.dispose();
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
      _bestPlant = null;
    });
    try {
      final recommendations = await _apiService.recommend(recommendationInput);
      if (!mounted) return;
      setState(() {
        _loadingRecommendations = false;
        _bestPlant = recommendations.bestPlant;
        _recommendations = recommendations.recommendations.take(5).toList();
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
        'soilPh': _soilPh.text.trim().isEmpty ? null : double.parse(_soilPh.text),
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
      backgroundColor: const Color(0xFFF4F8F1),
      appBar: AppBar(
        title: const Text('Plant Cultivation'),
        backgroundColor: const Color(0xFFF4F8F1),
        surfaceTintColor: Colors.transparent,
      ),
      body: Stack(
        children: [
          Positioned.fill(
            child: Opacity(
              opacity: 0.42,
              child: Image.network(
                'https://images.unsplash.com/photo-1464226184884-fa280b87c399?auto=format&fit=crop&w=1800&q=85',
                fit: BoxFit.cover,
                alignment: Alignment.topCenter,
                errorBuilder: (context, error, stackTrace) => Image.asset(
                  'assets/images/login_bg.png',
                  fit: BoxFit.cover,
                ),
              ),
            ),
          ),
          Positioned.fill(
            child: ColoredBox(color: Colors.white.withValues(alpha: 0.72)),
          ),
          Form(
            key: _formKey,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
              children: [
            const _CultivationHero(),
            const SizedBox(height: 16),
            const _CultivationTabs(),
            const SizedBox(height: 18),
            _Panel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _WeatherCard(status: _weatherStatus, loading: _loadingWeather, onRefresh: _detectWeather),
                  const SizedBox(height: 20),
                  const _SectionTitle(title: 'Weather data', icon: Icons.cloud_rounded),
                  const SizedBox(height: 12),
                  Row(children: [Expanded(child: _numberField(_temperature, 'Temperature', '°C')), const SizedBox(width: 12), Expanded(child: _numberField(_humidity, 'Humidity', '%'))]),
                  const SizedBox(height: 12),
                  _numberField(_rainfall, 'Rainfall', 'mm'),
                ],
              ),
            ),
            const SizedBox(height: 18),
            _Panel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _SectionTitle(title: 'Farm details', icon: Icons.agriculture_rounded),
                  const SizedBox(height: 12),
            _dropdown('What type of soil do you have?', _soilType, const [
              'Loamy - soft, balanced soil',
              'Sandy - loose and drains quickly',
              'Clay - heavy and holds water',
              'Silty - smooth and holds moisture',
              'Not sure - I do not know',
            ], (value) => setState(() => _soilType = value)),
            TextFormField(
              controller: _soilPh,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.]'))],
              validator: (value) {
                if (value == null || value.trim().isEmpty) return null;
                final ph = double.tryParse(value);
                return ph == null || ph < 0 || ph > 14 ? 'Enter a pH value from 0 to 14' : null;
              },
              decoration: const InputDecoration(
                labelText: 'Soil pH (optional)',
                hintText: 'Leave blank if you are not sure',
                helperText: 'You can still get recommendations without this value.',
                prefixIcon: Icon(Icons.science_outlined),
              ),
            ),
            const SizedBox(height: 12),
            _dropdown('What size is your growing area?', _landSize, const [
              'Under 1 perch',
              '1-5 perches',
              '6-10 perches',
              '11-20 perches',
              '21-50 perches',
              '51-100 perches',
              '101-500 perches',
              '1/4 acre',
              '1/2 acre',
              '1 acre',
              'More than 1 acre',
            ], (value) => setState(() => _landSize = value)),
            const SizedBox(height: 4),
            const Text('How much can you spend on growing this plant?', style: TextStyle(color: AppColors.text, fontSize: 16, fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            const Text('Enter your approximate budget for seeds/plants, soil, fertilizer and other basic gardening supplies.', style: TextStyle(color: AppColors.muted, fontSize: 13, fontWeight: FontWeight.w600)),
            const SizedBox(height: 10),
            LayoutBuilder(builder: (context, constraints) {
              final compact = constraints.maxWidth < 360;
              final currencyField = DropdownButtonFormField<String>(initialValue: _budgetCurrency, items: _currencies.map((currency) => DropdownMenuItem(value: currency, child: Text(currency))).toList(), onChanged: (value) => setState(() => _budgetCurrency = value ?? _budgetCurrency), decoration: const InputDecoration(prefixIcon: Icon(Icons.currency_exchange_rounded), contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 16)));
              final amountField = TextFormField(controller: _budgetAmount, keyboardType: TextInputType.number, inputFormatters: [FilteringTextInputFormatter.digitsOnly, _ThousandsSeparatorFormatter()], validator: (value) => value == null || value.trim().isEmpty ? 'Required' : null, decoration: const InputDecoration(labelText: 'Budget amount', hintText: 'Example: 5,000', prefixIcon: Icon(Icons.payments_outlined)));
              return compact ? Column(children: [currencyField, const SizedBox(height: 12), amountField]) : Row(children: [SizedBox(width: 118, child: currencyField), const SizedBox(width: 12), Expanded(child: amountField)]);
            }),
            const SizedBox(height: 12),
            _dropdown('How will you provide water?', _irrigation, const ['Rain only', 'Hand watering', 'Drip irrigation', 'Sprinkler', 'Hose', 'Other'], (value) => setState(() => _irrigation = value)),
            _dropdown('How much sunlight does the growing area get?', _sunlight, const ['Low sunlight - less than about 3 hours daily', 'Partial sunlight - about 3 to 6 hours daily', 'Full sunlight - about 6 or more hours daily'], (value) => setState(() => _sunlight = value)),
            _dropdown('When do you plan to plant?', _growingSeason, _months, (value) => setState(() => _growingSeason = value ?? _growingSeason)),
            _dropdown('How long do you want to grow the plant?', _growingDuration, const ['Short - a few weeks to a few months', 'Medium - several months', 'Long - many months or longer'], (value) => setState(() => _growingDuration = value)),
            const Padding(padding: EdgeInsets.only(top: 0, bottom: 4), child: Text('This is how long you are willing to wait before harvesting or seeing the plant mature.', style: TextStyle(color: AppColors.muted, fontSize: 13, fontWeight: FontWeight.w600))),
            const SizedBox(height: 20),
            FilledButton.icon(onPressed: _loadingRecommendations ? null : _submit, icon: _loadingRecommendations ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.eco_rounded), label: Text(_loadingRecommendations ? 'Finding suitable plants...' : 'Get crop recommendation'), style: FilledButton.styleFrom(backgroundColor: AppColors.primary, foregroundColor: Colors.white, minimumSize: const Size.fromHeight(54), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)))),
                ],
              ),
            ),
            if (_recommendationError != null) ...[
              const SizedBox(height: 12),
              Text(_recommendationError!, style: const TextStyle(color: AppColors.danger, fontWeight: FontWeight.w700)),
            ],
            if (_recommendations.isNotEmpty) ...[
              const SizedBox(height: 28),
              if (_bestPlant != null) ...[
                _BestPlantCard(recommendation: _bestPlant!),
                const SizedBox(height: 24),
              ],
              const _SectionTitle(title: 'Recommended plants', icon: Icons.local_florist_rounded),
              const SizedBox(height: 12),
              ..._recommendations.asMap().entries.map((entry) => _RecommendationCard(position: entry.key + 1, recommendation: entry.value)),
            ],
              ],
            ),
          ),
        ],
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

class _CultivationHero extends StatelessWidget {
  const _CultivationHero();

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(22),
      child: SizedBox(
        height: 176,
        child: Stack(
          fit: StackFit.expand,
          children: [
            Image.asset('assets/images/login_bg.png', fit: BoxFit.cover),
            Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.centerLeft,
                  end: Alignment.centerRight,
                  colors: [Color(0xF2FFFFFF), Color(0x90FFFFFF), Color(0x15FFFFFF)],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 18, 20, 18),
              child: Row(
                children: [
                  const Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Plan your crop', style: TextStyle(color: AppColors.text, fontSize: 27, fontWeight: FontWeight.w900)),
                        SizedBox(height: 7),
                        Text('Tell us about your growing space and we will find the best plants for you.', style: TextStyle(color: AppColors.muted, height: 1.3, fontWeight: FontWeight.w700)),
                      ],
                    ),
                  ),
                  Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.9), shape: BoxShape.circle),
                    child: const Icon(Icons.local_florist_rounded, color: AppColors.primary, size: 42),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CultivationTabs extends StatelessWidget {
  const _CultivationTabs();

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: const [
          _PlanTag(icon: Icons.auto_awesome_rounded, label: 'Smart plan', active: true),
          SizedBox(width: 8),
          _PlanTag(icon: Icons.cloud_rounded, label: 'Live weather'),
          SizedBox(width: 8),
          _PlanTag(icon: Icons.eco_rounded, label: 'Plant match'),
          SizedBox(width: 8),
          _PlanTag(icon: Icons.schedule_rounded, label: 'Best timing'),
        ],
      ),
    );
  }
}

class _PlanTag extends StatelessWidget {
  const _PlanTag({required this.icon, required this.label, this.active = false});

  final IconData icon;
  final String label;
  final bool active;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
      decoration: BoxDecoration(
        color: active ? AppColors.primary : Colors.white,
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: active ? AppColors.primary : AppColors.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: active ? Colors.white : AppColors.muted),
          const SizedBox(width: 6),
          Text(label, style: TextStyle(color: active ? Colors.white : AppColors.text, fontSize: 12, fontWeight: FontWeight.w800)),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, required this.icon});
  final String title;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Row(children: [Icon(icon, color: AppColors.primary, size: 21), const SizedBox(width: 8), Text(title, style: const TextStyle(color: AppColors.text, fontSize: 17, fontWeight: FontWeight.w900))]);
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: Colors.white.withValues(alpha: 0.95)),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF245A36).withValues(alpha: 0.08),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: child,
    );
  }
}

class _BestPlantCard extends StatelessWidget {
  const _BestPlantCard({required this.recommendation});

  final PlantRecommendation recommendation;

  @override
  Widget build(BuildContext context) {
    final details = <MapEntry<String, String?>>[
      MapEntry('Soil requirement', recommendation.soilRequirement),
      MapEntry('Sunlight requirement', recommendation.sunlightRequirement),
      MapEntry('Watering requirement', recommendation.wateringRequirement),
      MapEntry('Planting method', recommendation.plantingMethod),
      MapEntry('Fertilizer and care', recommendation.fertilizerCare),
      MapEntry('Growing period', recommendation.growingPeriod),
      MapEntry('Selling price', recommendation.sellingPrice),
      MapEntry('Harvesting', recommendation.harvestingInformation),
    ];
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFFF0FBEF),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.primary.withValues(alpha: 0.45), width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(color: AppColors.primary.withValues(alpha: 0.16), shape: BoxShape.circle),
                child: const Icon(Icons.local_florist_rounded, color: AppColors.primary, size: 30),
              ),
              const SizedBox(width: 12),
              const Expanded(child: Text('Best Plant for You', style: TextStyle(color: AppColors.primary, fontSize: 14, fontWeight: FontWeight.w900))),
              if (recommendation.score > 0) Text('${recommendation.score} pts', style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w900)),
            ],
          ),
          const SizedBox(height: 14),
          Text(recommendation.name, style: const TextStyle(color: AppColors.text, fontSize: 25, fontWeight: FontWeight.w900)),
          const SizedBox(height: 6),
          Text(recommendation.whySuitable ?? recommendation.reason, style: const TextStyle(color: AppColors.muted, height: 1.35, fontWeight: FontWeight.w600)),
          const SizedBox(height: 16),
          ...details.where((detail) => detail.value != null).map((detail) => Padding(
                padding: const EdgeInsets.only(bottom: 9),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [SizedBox(width: 126, child: Text(detail.key, style: const TextStyle(color: AppColors.text, fontSize: 12, fontWeight: FontWeight.w900))), Expanded(child: Text(detail.value!, style: const TextStyle(color: AppColors.muted, fontSize: 12, fontWeight: FontWeight.w600)))]),
              )),
        ],
      ),
    );
  }
}

class _RecommendationCard extends StatelessWidget {
  const _RecommendationCard({required this.position, required this.recommendation});

  final int position;
  final PlantRecommendation recommendation;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'View details for ${recommendation.name}',
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => showModalBottomSheet<void>(
          context: context,
          isScrollControlled: true,
          backgroundColor: Colors.transparent,
          builder: (_) => _PlantDetailsSheet(recommendation: recommendation),
        ),
        child: Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: AppColors.border)),
          child: Row(
            children: [
              CircleAvatar(radius: 18, backgroundColor: AppColors.primary.withValues(alpha: 0.12), child: Text('$position', style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w900))),
              const SizedBox(width: 12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(recommendation.name, style: const TextStyle(color: AppColors.text, fontSize: 16, fontWeight: FontWeight.w800)), const SizedBox(height: 3), Text(recommendation.reason, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: AppColors.muted, fontSize: 12, fontWeight: FontWeight.w600))])),
              const Icon(Icons.arrow_forward_ios_rounded, color: AppColors.muted, size: 16),
            ],
          ),
        ),
      ),
    );
  }
}

class _PlantDetailsSheet extends StatelessWidget {
  const _PlantDetailsSheet({required this.recommendation});

  final PlantRecommendation recommendation;

  @override
  Widget build(BuildContext context) {
    final details = <MapEntry<String, String?>>[
      MapEntry('Soil requirement', recommendation.soilRequirement),
      MapEntry('Sunlight requirement', recommendation.sunlightRequirement),
      MapEntry('Watering requirement', recommendation.wateringRequirement),
      MapEntry('Planting method', recommendation.plantingMethod),
      MapEntry('Fertilizer and care', recommendation.fertilizerCare),
      MapEntry('Growing period', recommendation.growingPeriod),
      MapEntry('Selling price', recommendation.sellingPrice),
      MapEntry('Harvesting', recommendation.harvestingInformation),
    ];
    return Container(
      constraints: const BoxConstraints(maxHeight: 680),
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      child: SingleChildScrollView(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Center(child: Container(width: 42, height: 4, decoration: BoxDecoration(color: AppColors.border, borderRadius: BorderRadius.circular(4)))),
          const SizedBox(height: 18),
          Row(children: [Container(width: 48, height: 48, decoration: BoxDecoration(color: AppColors.primary.withValues(alpha: 0.14), shape: BoxShape.circle), child: const Icon(Icons.local_florist_rounded, color: AppColors.primary, size: 28)), const SizedBox(width: 12), Expanded(child: Text(recommendation.name, style: const TextStyle(color: AppColors.text, fontSize: 24, fontWeight: FontWeight.w900))), Text('${recommendation.score} pts', style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w900))]),
          const SizedBox(height: 10),
          Text(recommendation.whySuitable ?? recommendation.reason, style: const TextStyle(color: AppColors.muted, height: 1.35, fontWeight: FontWeight.w600)),
          const SizedBox(height: 18),
          ...details.where((detail) => detail.value != null).map((detail) => Padding(padding: const EdgeInsets.only(bottom: 12), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [SizedBox(width: 132, child: Text(detail.key, style: const TextStyle(color: AppColors.text, fontSize: 12, fontWeight: FontWeight.w900))), Expanded(child: Text(detail.value!, style: const TextStyle(color: AppColors.muted, fontSize: 12, fontWeight: FontWeight.w600)))]))),
        ]),
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
