import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
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

  testWidgets('HomeScreen renders schedules with toggle switch and edit button', (tester) async {
    const account = Account(id: 1, email: 'caregiver-a@example.test', displayName: 'Người thân A', role: 'caregiver');
    const patient = Patient(id: 1, name: 'Hồ sơ A');
    const schedule = MedicationSchedule(
      id: 10,
      patientId: 1,
      medicationName: 'Thuốc A',
      slot: 1,
      time: '08:00',
      active: true,
    );

    int? updatedScheduleId;
    Map<String, dynamic>? updatedValues;

    await tester.pumpWidget(
      MaterialApp(
        home: HomeScreen(
          account: account,
          patients: const [patient],
          schedules: const [schedule],
          onCreateSchedule: (_) async {},
          onUpdateSchedule: (id, values) async {
            updatedScheduleId = id;
            updatedValues = values;
          },
          onLogout: () {},
        ),
      ),
    );

    // Kiểm tra thông tin hiển thị
    expect(find.text('Thuốc A'), findsWidgets);
    expect(find.text('08:00'), findsWidgets);
    expect(find.byType(Switch), findsWidgets);
    expect(find.byIcon(Icons.edit_outlined), findsWidgets);

    // Thao tác gạt công tắc để tắt lịch
    final switchFinder = find.byType(Switch).first;
    await tester.tap(switchFinder);
    await tester.pumpAndSettle();

    // Xác nhận đã gọi hàm cập nhật với id và active = false
    expect(updatedScheduleId, equals(10));
    expect(updatedValues?['active'], isFalse);

    // Nhấn nút sửa lịch để mở dialog
    final editButton = find.byIcon(Icons.edit_outlined).first;
    await tester.tap(editButton);
    await tester.pumpAndSettle();

    expect(find.text('Chỉnh sửa lịch uống thuốc'), findsOneWidget);
    expect(find.text('Lưu thay đổi'), findsOneWidget);
  });
}
