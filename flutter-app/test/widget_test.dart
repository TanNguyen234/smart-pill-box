import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:smart_pill_box/api/smart_pill_api.dart';
import 'package:smart_pill_box/main.dart';
import 'package:smart_pill_box/models.dart';
import 'package:smart_pill_box/screens/home_screen.dart';

void main() {
  testWidgets('shows the caregiver sign-in screen', (tester) async {
    await tester.pumpWidget(const SmartPillBoxApp());
    expect(find.text('SMART PILL BOX'), findsOneWidget);
    expect(find.text('Đăng nhập'), findsOneWidget);
    expect(find.text('caregiver-a@example.test'), findsOneWidget);
  });

  testWidgets('renders HomeScreen and switches between 5 tabs', (tester) async {
    final mockClient = MockClient((request) async {
      if (request.url.path.contains('/api/doses')) {
        return http.Response(
          jsonEncode([
            {
              'id': 1,
              'schedule_id': 1,
              'patient_id': 1,
              'slot': 1,
              'medication_name': 'Amlodipin 5mg',
              'scheduled_at': '2026-10-17T08:00:00+07:00',
              'confirmed_at': null,
              'status': 'PENDING',
              'reminder_count': 0,
              'created_at': '2026-10-17T07:00:00+07:00'
            }
          ]),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      if (request.url.path.contains('/api/alerts')) {
        return http.Response(
          jsonEncode([
            {
              'id': 1,
              'patient_id': 1,
              'patient_name': 'Nguyễn Văn An',
              'slot': 1,
              'medication_name': 'Amlodipin 5mg',
              'alert_type': 'MISSED_DOSE',
              'recipient_id': 1,
              'status': 'PENDING',
              'message': 'Đã quá hạn uống thuốc ngăn 1',
              'note': null,
              'created_at': '2026-10-17T08:05:00+07:00',
              'resolved_at': null
            }
          ]),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      if (request.url.path.contains('/api/events')) {
        return http.Response(
          jsonEncode([
            {
              'id': 1,
              'event_uuid': 'uuid-1',
              'patient_id': 1,
              'slot': 1,
              'event_type': 'LID_OPENED',
              'payload': {},
              'occurred_at': '2026-10-17T08:00:00+07:00',
              'created_at': '2026-10-17T08:00:00+07:00'
            }
          ]),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      return http.Response('[]', 200, headers: {'content-type': 'application/json'});
    });

    final api = SmartPillApi(client: mockClient);
    api.token = 'test-jwt-token';
    final account = Account(id: 1, email: 'caregiver-a@example.test', displayName: 'Người thân A', role: 'caregiver');
    final patient = const Patient(id: 1, name: 'Nguyễn Văn An');
    final schedule = MedicationSchedule(id: 1, patientId: 1, medicationName: 'Amlodipin 5mg', slot: 1, time: '08:00', active: true);

    await tester.pumpWidget(MaterialApp(
      home: HomeScreen(
        account: account,
        patients: [patient],
        schedules: [schedule],
        api: api,
        onCreateSchedule: (vals) async {},
        onUpdateSchedule: (id, vals) async {},
        onRefreshData: () async {},
        onLogout: () {},
      ),
    ));

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // Verify Tab 0: Hôm nay
    expect(find.text('Hôm nay'), findsWidgets);
    expect(find.text('Amlodipin 5mg'), findsWidgets);

    // Switch to Tab 1: Lịch
    await tester.tap(find.text('Lịch'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('Quản lý lịch uống'), findsOneWidget);
    expect(find.text('Thêm lịch'), findsOneWidget);

    // Switch to Tab 2: Lịch sử
    await tester.tap(find.text('Lịch sử'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('Lịch sử sự kiện'), findsOneWidget);

    // Switch to Tab 3: Cảnh báo
    await tester.tap(find.text('Cảnh báo'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('Danh sách cảnh báo'), findsOneWidget);

    // Switch to Tab 4: Tài khoản
    await tester.tap(find.text('Tài khoản'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('Hồ sơ được chăm sóc'), findsOneWidget);
    expect(find.text('Người thân A'), findsOneWidget);
    expect(find.text('caregiver-a@example.test'), findsOneWidget);
    expect(find.text('Đăng xuất'), findsOneWidget);
  });

  testWidgets('displays recurrence label and deletes a schedule with confirmation', (tester) async {
    final account = Account(id: 1, email: 'caregiver-a@example.test', displayName: 'Người thân A', role: 'caregiver');
    final patient = const Patient(id: 1, name: 'Nguyễn Văn An');
    final schedule = MedicationSchedule(
      id: 42,
      patientId: 1,
      medicationName: 'Metformin 500mg',
      slot: 2,
      time: '12:00',
      active: true,
      daysOfWeek: '1,3,5',
    );

    int? deletedScheduleId;
    final api = SmartPillApi(client: MockClient((_) async => http.Response('[]', 200, headers: {'content-type': 'application/json'})));
    api.token = 'test-jwt-token';

    await tester.pumpWidget(MaterialApp(
      home: HomeScreen(
        account: account,
        patients: [patient],
        schedules: [schedule],
        api: api,
        onCreateSchedule: (vals) async {},
        onUpdateSchedule: (id, vals) async {},
        onDeleteSchedule: (id) async {
          deletedScheduleId = id;
        },
        onRefreshData: () async {},
        onLogout: () {},
      ),
    ));

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // Verify recurrence label on Tab 0
    expect(find.textContaining('Thứ 2, 4, 6'), findsOneWidget);

    // Switch to Tab 1 (Lịch)
    await tester.tap(find.text('Lịch'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Metformin 500mg'), findsOneWidget);
    expect(find.text('Thứ 2, 4, 6'), findsOneWidget);

    // Tap delete button
    final deleteButton = find.byTooltip('Xóa lịch uống');
    expect(deleteButton, findsOneWidget);
    await tester.tap(deleteButton);
    await tester.pumpAndSettle();

    // Verify confirmation dialog
    expect(find.text('Xác nhận xóa lịch uống'), findsOneWidget);
    expect(find.textContaining('Bạn có chắc chắn muốn xóa lịch uống "Metformin 500mg"'), findsOneWidget);

    // Confirm deletion
    await tester.tap(find.widgetWithText(FilledButton, 'Xóa lịch'));
    await tester.pumpAndSettle();

    expect(deletedScheduleId, 42);
  });
}
