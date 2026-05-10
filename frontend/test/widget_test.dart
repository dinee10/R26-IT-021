import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/main.dart';

void main() {
  testWidgets('shows the detector screen', (WidgetTester tester) async {
    await tester.pumpWidget(const HerbalDetectorApp());

    expect(find.text('Herbal Plant Detector'), findsOneWidget);
    expect(find.text('Image Set'), findsOneWidget);
    expect(find.text('Result'), findsOneWidget);
  });
}
