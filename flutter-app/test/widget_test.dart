import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_pill_box/main.dart';
import 'package:smart_pill_box/models.dart';
import 'package:smart_pill_box/screens/alerts_screen.dart';
import 'package:smart_pill_box/screens/history_screen.dart';

void main() {
  testWidgets('shows the caregiver sign-in screen', (tester) async {
    await tester.pumpWidget(const SmartPillBoxApp());
    expect(find.text('SMART PILL BOX'), findsOneWidget);
    expect(find.text('Đăng nhập'), findsOneWidget);
    expect(find.text('caregiver-a@example.test'), findsOneWidget);
  });

  testWidgets('HistoryScreen filters events by slot', (tester) async {
    final sampleEvents = [
      const DeviceEventItem(
        id: 1,
        eventUuid: 'uuid-1',
        eventType: 'LID_OPENED',
        slot: 1,
        payload: {'slot': 1},
        timestamp: '2026-10-09T08:00:00+07:00',
        createdAt: '2026-10-09T08:00:00Z',
      ),
      const DeviceEventItem(
        id: 2,
        eventUuid: 'uuid-2',
        eventType: 'CONFIRM_PRESSED',
        slot: 2,
        payload: {'slot': 2},
        timestamp: '2026-10-09T12:00:00+07:00',
        createdAt: '2026-10-09T12:00:00Z',
      ),
    ];

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: HistoryScreen(initialEvents: sampleEvents),
        ),
      ),
    );

    expect(find.text('Mở nắp ngăn thuốc'), findsOneWidget);
    expect(find.text('Đã xác nhận uống thuốc'), findsOneWidget);

    await tester.tap(find.text('Ngăn 1'));
    await tester.pumpAndSettle();

    expect(find.text('Mở nắp ngăn thuốc'), findsOneWidget);
    expect(find.text('Đã xác nhận uống thuốc'), findsNothing);
  });

  testWidgets('AlertsScreen requires note when choosing Bỏ qua (IGNORED)', (tester) async {
    final sampleAlerts = [
      const AlertItem(
        id: 1,
        patientId: 1,
        kind: 'dose_overdue',
        status: 'PENDING',
        message: 'Chưa xác nhận Thuốc A ở ngăn 1',
        createdAt: '2026-10-09T08:05:00+07:00',
      ),
    ];

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AlertsScreen(initialAlerts: sampleAlerts),
        ),
      ),
    );

    expect(find.text('Chưa xác nhận Thuốc A ở ngăn 1'), findsOneWidget);

    await tester.tap(find.text('Chưa xác nhận Thuốc A ở ngăn 1'));
    await tester.pumpAndSettle();

    expect(find.text('Xử lý cảnh báo'), findsOneWidget);

    await tester.tap(find.text('Bỏ qua'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Xác nhận'));
    await tester.pumpAndSettle();

    expect(
      find.text('Vui lòng nhập lý do khi chọn Bỏ qua cảnh báo.'),
      findsOneWidget,
    );

    await tester.enterText(find.byType(TextField), 'Bệnh nhân đã báo uống bên ngoài');
    await tester.tap(find.text('Xác nhận'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Trạng thái: Bỏ qua'), findsOneWidget);
  });
}
