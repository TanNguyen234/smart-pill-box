import 'dart:async';

import 'package:flutter/material.dart';

import '../models.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    required this.account,
    required this.patients,
    required this.schedules,
    required this.onCreateSchedule,
    required this.onLogout,
    required this.onFetchAlerts,
    required this.onResolveAlert,
    this.onFetchVirtualClock,
  });

  final Account account;
  final List<Patient> patients;
  final List<MedicationSchedule> schedules;
  final Future<void> Function(Map<String, dynamic>) onCreateSchedule;
  final VoidCallback onLogout;
  final Future<List<Alert>> Function() onFetchAlerts;
  final Future<void> Function(int, String?) onResolveAlert;
  final Future<String> Function()? onFetchVirtualClock;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _page = 0;
  List<Alert> _alerts = [];
  bool _isLoadingAlerts = false;
  Timer? _clockTimer;
  String _virtualClock = '07:59:00';

  @override
  void initState() {
    super.initState();
    _fetchClock();
    _clockTimer = Timer.periodic(const Duration(seconds: 2), (_) {
      _fetchClock();
      if (_page == 3) {
        _loadAlerts();
      }
    });
  }

  @override
  void dispose() {
    _clockTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchClock() async {
    if (widget.onFetchVirtualClock != null) {
      final clock = await widget.onFetchVirtualClock!();
      if (mounted && clock.isNotEmpty) {
        setState(() => _virtualClock = clock);
      }
    }
  }

  @override
  void didUpdateWidget(HomeScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    _fetchClock();
  }

  String _formatClock(String raw) {
    if (raw.isEmpty) return '07:59:00';
    if (raw.contains('T')) {
      final timePart = raw.split('T')[1];
      final cleanTime = timePart.split('+')[0].split('-')[0].split('Z')[0];
      if (cleanTime.length >= 5) {
        return cleanTime;
      }
    }
    return raw;
  }

  String _getRemindStatus() {
    try {
      int currentMinutes = 7 * 60 + 59;
      if (_virtualClock.contains('T')) {
        final timeStr = _virtualClock.split('T')[1].split('+')[0].split('-')[0].split('Z')[0];
        final parts = timeStr.split(':');
        if (parts.length >= 2) {
          currentMinutes = int.parse(parts[0]) * 60 + int.parse(parts[1]);
        }
      }
      for (final s in widget.schedules) {
        if (!s.active) continue;
        final parts = s.time.split(':');
        final sMinutes = int.parse(parts[0]) * 60 + int.parse(parts[1]);
        final diff = currentMinutes - sMinutes;
        if (diff >= 0 && diff < 5) {
          return 'Đang đến giờ uống ${s.medicationName} (Ngăn ${s.slot})';
        } else if (diff >= 5 && diff < 120) {
          return 'Đã qua giờ uống ${s.medicationName} lúc ${s.time}';
        }
      }
    } catch (_) {}
    return 'Chưa đến giờ uống theo lịch.';
  }

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
        actions: [
          IconButton(
            icon: const Icon(Icons.sync),
            tooltip: 'Đồng bộ giờ',
            onPressed: () async {
              await _fetchClock();
              if (_page == 3) await _loadAlerts();
            },
          ),
        ],
        backgroundColor: const Color(0xFFF5F4EE),
      ),
      body: IndexedStack(index: _page, children: [
        _todayPage(context),
        _schedulesPage(context),
        _comingSoon(context, Icons.history, 'Lịch sử', 'Danh sách lần uống sẽ xuất hiện khi engine lịch được triển khai.'),
        _alertsPage(context),
        _accountPage(context),
      ]),
      floatingActionButton: _page == 1
          ? FloatingActionButton.extended(onPressed: _showCreateSchedule, icon: const Icon(Icons.add), label: const Text('Thêm lịch'))
          : null,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _page,
        onDestinationSelected: (index) {
          setState(() => _page = index);
          if (index == 3) _loadAlerts();
          _fetchClock();
        },
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
    return RefreshIndicator(
      onRefresh: () async {
        await _fetchClock();
        if (_page == 3) await _loadAlerts();
      },
      child: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
      Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: colors.primary, borderRadius: BorderRadius.circular(22)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('CHĂM SÓC HÔM NAY', style: TextStyle(color: Colors.white70, fontSize: 11, letterSpacing: 1.3)),
          const SizedBox(height: 10),
          Text(widget.patients.isEmpty ? 'Chưa có hồ sơ' : widget.patients.first.name, style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Text('Giờ demo: ${_formatClock(_virtualClock)} · GMT+7', style: const TextStyle(color: Colors.white70)),
          const SizedBox(height: 16),
          Row(children: [const Icon(Icons.info_outline, color: Color(0xFFD9E9A8), size: 17), const SizedBox(width: 8), Expanded(child: Text(_getRemindStatus(), style: const TextStyle(color: Colors.white, fontSize: 13)))]),
        ]),
      ),
      const SizedBox(height: 23),
      Text('Lịch uống trong ngày', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
      const SizedBox(height: 10),
      if (widget.schedules.isEmpty) _emptyCard(context, 'Chưa có lịch uống. Hãy thêm lịch mới để bắt đầu.') else ...widget.schedules.map((schedule) => _scheduleCard(context, schedule)),
      const SizedBox(height: 10),
      Text('Thông tin này lấy từ máy chủ demo. Chưa có xác nhận uống hoặc cảnh báo.', style: TextStyle(color: colors.onSurfaceVariant, fontSize: 12, height: 1.4)),
    ]),
  );
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

  Future<void> _loadAlerts() async {
    setState(() => _isLoadingAlerts = true);
    try {
      final alerts = await widget.onFetchAlerts();
      if (mounted) setState(() => _alerts = alerts);
    } finally {
      if (mounted) setState(() => _isLoadingAlerts = false);
    }
  }

  Future<void> _resolveAlert(Alert alert) async {
    final noteController = TextEditingController();
    final note = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Xử lý cảnh báo'),
        content: TextField(
          controller: noteController,
          decoration: const InputDecoration(hintText: 'Nhập ghi chú xử lý...'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: const Text('Huỷ')),
          FilledButton(onPressed: () => Navigator.pop(c, noteController.text), child: const Text('Xác nhận')),
        ],
      ),
    );
    if (note != null) {
      await widget.onResolveAlert(alert.id, note.isEmpty ? null : note);
      await _loadAlerts();
    }
  }

  Widget _alertsPage(BuildContext context) => _isLoadingAlerts
      ? const Center(child: CircularProgressIndicator())
      : ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text('Danh sách cảnh báo', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 10),
            if (_alerts.isEmpty) _emptyCard(context, 'Chưa có cảnh báo nào.') else ..._alerts.map((alert) {
              final isResolved = alert.resolvedAt != null;
              return Card(
                color: isResolved ? null : const Color(0xFFFFEBEB),
                child: ListTile(
                  leading: Icon(Icons.warning, color: isResolved ? Colors.grey : Colors.red),
                  title: Text(alert.message, style: TextStyle(color: isResolved ? Colors.grey : Colors.red.shade900, fontWeight: FontWeight.w600)),
                  subtitle: Text('Loại: ${alert.kind} - Lần nhắc: ${alert.occurrenceId}\nThời gian: ${alert.createdAt}'),
                  trailing: isResolved
                      ? const Icon(Icons.check_circle, color: Colors.green)
                      : TextButton(onPressed: () => _resolveAlert(alert), child: const Text('XỬ LÝ')),
                  isThreeLine: true,
                ),
              );
            }),
          ],
        );

}
