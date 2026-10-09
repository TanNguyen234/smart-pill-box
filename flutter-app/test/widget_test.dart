import 'package:flutter_test/flutter_test.dart';
import 'package:smart_pill_box/main.dart';

void main() {
  testWidgets('shows the caregiver sign-in screen', (tester) async {
    await tester.pumpWidget(const SmartPillBoxApp());
    expect(find.text('SMART PILL BOX'), findsOneWidget);
    expect(find.text('Đăng nhập'), findsOneWidget);
    expect(find.text('caregiver-a@example.test'), findsOneWidget);
  });
}
