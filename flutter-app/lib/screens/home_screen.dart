import 'package:flutter/material.dart';

import '../models.dart';
import 'history_screen.dart';
import 'alerts_screen.dart';
class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    required this.account,
    required this.patients,
    required this.schedules,
    required this.onCreateSchedule,
    required this.onLogout,
  });

  final Account account;
  final List<Patient> patients;
  final List<MedicationSchedule> schedules;
  final Future<void> Function(Map<String, dynamic>) onCreateSchedule;
  final VoidCallback onLogout;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _page = 0;

  Future<void> _showCreateSchedule() async {
    if (widget.patients.isEmpty) return;
    final formKey = GlobalKey<FormState>();
    final name = TextEditingController();
    var patientId = widget.patients.first.id;
    var slot = 1;
    var time = const TimeOfDay(hour: 8, minute: 0);
    var busy = false;
    String? error;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Thêm lịch uống thuốc'),
          content: Form(
            key: formKey,
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                DropdownButtonFormField<int>(
                  initialValue: patientId,
                  decoration: const InputDecoration(labelText: 'Người được chăm sóc'),
                  items: widget.patients.map((p) => DropdownMenuItem(value: p.id, child: Text(p.name))).toList(),
                  onChanged: (value) => patientId = value ?? patientId,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: name,
                  decoration: const InputDecoration(labelText: 'Tên thuốc mẫu'),
                  validator: (value) => value == null || value.trim().isEmpty ? 'Nhập tên thuốc' : null,
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<int>(
                  initialValue: slot,
                  decoration: const InputDecoration(labelText: 'Ngăn thuốc'),
                  items: List.generate(3, (i) => DropdownMenuItem(value: i + 1, child: Text('Ngăn ${i + 1}'))),
                  onChanged: (value) => slot = value ?? slot,
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: () async {
                    final chosen = await showTimePicker(context: context, initialTime: time);
                    if (chosen != null) setDialogState(() => time = chosen);
                  },
                  icon: const Icon(Icons.schedule),
                  label: Text('Giờ uống: ${time.format(context)}'),
                ),
                if (error != null) ...[
                  const SizedBox(height: 10),
                  Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                ],
              ]),
            ),
          ),
          actions: [
            TextButton(onPressed: busy ? null : () => Navigator.pop(dialogContext), child: const Text('Hủy')),
            FilledButton(
              onPressed: busy
                  ? null
                  : () async {
                      if (!formKey.currentState!.validate()) return;
                      setDialogState(() {
                        busy = true;
                        error = null;
                      });
                      try {
                        await widget.onCreateSchedule({
                          'patient_id': patientId,
                          'medication_name': name.text.trim(),
                          'slot': slot,
                          'time': '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}',
                        });
                        if (dialogContext.mounted) Navigator.pop(dialogContext);
                      } catch (exception) {
                        setDialogState(() {
                          busy = false;
                          error = exception.toString();
                        });
                      }
                    },
              child: Text(busy ? 'Đang lưu…' : 'Lưu lịch'),
            ),
          ],
        ),
      ),
    );
    name.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final titles = ['Hôm nay', 'Lịch uống', 'Lịch sử', 'Cảnh báo', 'Tài khoản'];
    return Scaffold(
      appBar: AppBar(
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('SMART PILL BOX', style: TextStyle(fontSize: 12, letterSpacing: 1.4, fontWeight: FontWeight.w700)),
          Text(titles[_page], style: TextStyle(fontSize: 12, color: colors.onSurfaceVariant, fontWeight: FontWeight.normal)),
        ]),
        backgroundColor: const Color(0xFFF5F4EE),
      ),
      body: IndexedStack(index: _page, children: [
        _todayPage(context),
        _schedulesPage(context),
        HistoryScreen(),
        AlertsScreen(),
        _accountPage(context),
      ]),
      floatingActionButton: _page == 1
          ? FloatingActionButton.extended(onPressed: _showCreateSchedule, icon: const Icon(Icons.add), label: const Text('Thêm lịch'))
          : null,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _page,
        onDestinationSelected: (index) => setState(() => _page = index),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.today_outlined), selectedIcon: Icon(Icons.today), label: 'Hôm nay'),
          NavigationDestination(icon: Icon(Icons.calendar_month_outlined), selectedIcon: Icon(Icons.calendar_month), label: 'Lịch'),
          NavigationDestination(icon: Icon(Icons.history), label: 'Lịch sử'),
          NavigationDestination(icon: Icon(Icons.notifications_none), label: 'Cảnh báo'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'Tài khoản'),
        ],
      ),
    );
  }

  Widget _todayPage(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
      Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: colors.primary, borderRadius: BorderRadius.circular(22)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('CHĂM SÓC HÔM NAY', style: TextStyle(color: Colors.white70, fontSize: 11, letterSpacing: 1.3)),
          const SizedBox(height: 10),
          Text(widget.patients.isEmpty ? 'Chưa có hồ sơ' : widget.patients.first.name, style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          const Text('Giờ demo: 07:59 · GMT+7', style: TextStyle(color: Colors.white70)),
          const SizedBox(height: 16),
          const Row(children: [Icon(Icons.info_outline, color: Color(0xFFD9E9A8), size: 17), SizedBox(width: 8), Expanded(child: Text('Chưa đến giờ uống theo lịch.', style: TextStyle(color: Colors.white, fontSize: 13)))]),
        ]),
      ),
      const SizedBox(height: 23),
      Text('Lịch uống trong ngày', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
      const SizedBox(height: 10),
      if (widget.schedules.isEmpty) _emptyCard(context, 'Chưa có lịch uống. Hãy thêm lịch mới để bắt đầu.') else ...widget.schedules.map((schedule) => _scheduleCard(context, schedule)),
      const SizedBox(height: 10),
      Text('Thông tin này lấy từ máy chủ demo. Chưa có xác nhận uống hoặc cảnh báo.', style: TextStyle(color: colors.onSurfaceVariant, fontSize: 12, height: 1.4)),
    ]);
  }

  Widget _schedulesPage(BuildContext context) => ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 90), children: [
        Text('Lịch đã lưu', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
        const SizedBox(height: 6),
        Text('Các thay đổi được lưu trực tiếp vào backend.', style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant)),
        const SizedBox(height: 16),
        if (widget.schedules.isEmpty) _emptyCard(context, 'Chưa có lịch. Nhấn “Thêm lịch” để tạo.') else ...widget.schedules.map((schedule) => _scheduleCard(context, schedule)),
      ]);

  Widget _scheduleCard(BuildContext context, MedicationSchedule schedule) {
    final patient = widget.patients.where((item) => item.id == schedule.patientId).firstOrNull;
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
        leading: CircleAvatar(backgroundColor: const Color(0xFFE6ECDB), child: Text('${schedule.slot}', style: const TextStyle(fontWeight: FontWeight.w700))),
        title: Text(schedule.medicationName, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text('${patient?.name ?? 'Hồ sơ'} · Ngăn ${schedule.slot} · ${schedule.active ? 'Đang bật' : 'Đang tắt'}'),
        trailing: Text(schedule.time, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
      ),
    );
  }

  Widget _comingSoon(BuildContext context, IconData icon, String title, String description) => Center(
        child: Padding(
          padding: const EdgeInsets.all(36),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(icon, size: 44, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 16),
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(description, textAlign: TextAlign.center, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, height: 1.5)),
            const SizedBox(height: 14),
            const Chip(label: Text('Sẽ phát triển ở giai đoạn sau')),
          ]),
        ),
      );

  Widget _accountPage(BuildContext context) => ListView(padding: const EdgeInsets.all(20), children: [
        Card(child: ListTile(leading: const CircleAvatar(child: Icon(Icons.person)), title: Text(widget.account.displayName), subtitle: Text(widget.account.email))),
        const SizedBox(height: 8),
        Card(child: ListTile(leading: const Icon(Icons.people_outline), title: const Text('Hồ sơ được chăm sóc'), trailing: Text('${widget.patients.length}'))),
        const SizedBox(height: 20),
        OutlinedButton.icon(onPressed: widget.onLogout, icon: const Icon(Icons.logout), label: const Text('Đăng xuất')),
      ]);

  Widget _emptyCard(BuildContext context, String message) => Card(child: Padding(padding: const EdgeInsets.all(18), child: Text(message, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant))));
}
