import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/screens/identify_plant_page.dart';

void main() {
  testWidgets('identify page exposes detector controls', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: IdentifyPlantPage()));

    expect(find.text('Identify Plant'), findsOneWidget);
    expect(find.text('Leaf / plant'), findsOneWidget);
    expect(find.text('Seed / spice'), findsOneWidget);
    expect(find.text('Add 1 to 5 photos'), findsOneWidget);
    expect(find.text('Gallery'), findsOneWidget);
    expect(find.text('Camera'), findsOneWidget);
    expect(find.text('Identify from photos'), findsOneWidget);
  });

  testWidgets('identify requires at least one image', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: IdentifyPlantPage()));

    final identifyButton = find.text('Identify from photos');
    await tester.drag(find.byType(ListView), const Offset(0, -220));
    await tester.pumpAndSettle();
    await tester.tap(identifyButton);
    await tester.pump();

    expect(find.text('Add at least one clear image first.'), findsOneWidget);
  });
}
