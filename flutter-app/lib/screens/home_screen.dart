import 'package:flutter/material.dart';

import '../models.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    required this.account,
    required this.patients,
    required this.schedules,
    required this.onCreateSchedule,
    this.onUpdateSchedule,
    required this.onLogout,
  });

  final Account account;
  final List<Patient> patients;
  final List<MedicationSchedule> schedules;
  final Future<void> Function(Map<String, dynamic>) onCreateSchedule;
  final Future<void> Function(int scheduleId, Map<String, dynamic> values)? onUpdateSchedule;
  final VoidCallback onLogout;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _page = 0;
  late List<MedicationSchedule> _localSchedules;
  final Set<int> _updatingScheduleIds = {};
  int? _selectedPatientId;

  @override
  void initState() {
    super.initState();
    _localSchedules = List.from(widget.schedules);
    if (widget.patients.isNotEmpty) {
      _selectedPatientId = widget.patients.first.id;
    }
  }

  @override
  void didUpdateWidget(HomeScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.schedules != widget.schedules) {
      _localSchedules = List.from(widget.schedules);
    }
    if (_selectedPatientId == null && widget.patients.isNotEmpty) {
      _selectedPatientId = widget.patients.first.id;
    }
  }

  // ==================== VIỆC 4: BẬT / TẮT LỊCH (TOGGLE VỚI ROLLBACK) ====================
  Future<void> _toggleSchedule(MedicationSchedule schedule, bool newValue) async {
    final index = _localSchedules.indexWhere((s) => s.id == schedule.id);
    if (index == -1) return;

    // Cập nhật lạc quan trên giao diện ngay lập tức
    setState(() {
      _localSchedules[index] = _localSchedules[index].copyWith(active: newValue);
      _updatingScheduleIds.add(schedule.id);
    });

    try {
      if (widget.onUpdateSchedule != null) {
        await widget.onUpdateSchedule!(schedule.id, {'active': newValue});
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${schedule.medicationName}: ${newValue ? "Đã bật lịch" : "Đã tạm dừng lịch"}'),
            duration: const Duration(seconds: 2),
            backgroundColor: const Color(0xFF315C49),
          ),
        );
      }
    } catch (e) {
      // ROLLBACK: Nếu máy chủ lỗi hoặc rớt mạng, gạt switch quay về trạng thái cũ
      if (mounted) {
        setState(() {
          final rollbackIdx = _localSchedules.indexWhere((s) => s.id == schedule.id);
          if (rollbackIdx != -1) {
            _localSchedules[rollbackIdx] = _localSchedules[rollbackIdx].copyWith(active: !newValue);
          }
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Lỗi cập nhật: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _updatingScheduleIds.remove(schedule.id));
      }
    }
  }

  // ==================== VIỆC 4: FORM CHỈNH SỬA LỊCH ĐẦY ĐỦ ====================
  Future<void> _showEditSchedule(MedicationSchedule schedule) async {
    final patient = widget.patients.where((p) => p.id == schedule.patientId).firstOrNull;
    final success = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _EditScheduleDialog(
        schedule: schedule,
        patient: patient,
        onSubmit: (values) async {
          if (widget.onUpdateSchedule != null) {
            await widget.onUpdateSchedule!(schedule.id, values);
          }
        },
      ),
    );

    if (success == true && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Đã cập nhật lịch uống thuốc thành công.'),
          backgroundColor: Color(0xFF315C49),
        ),
      );
    }
  }

  // ==================== VIỆC 4: THÊM LỊCH ====================
  Future<void> _showCreateSchedule() async {
    if (widget.patients.isEmpty) return;
    final initialPatientId = _selectedPatientId ?? widget.patients.first.id;

    final success = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _CreateScheduleDialog(
        patients: widget.patients,
        initialPatientId: initialPatientId,
        onSubmit: widget.onCreateSchedule,
      ),
    );

    if (success == true && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Đã thêm lịch uống thuốc thành công.'),
          backgroundColor: Color(0xFF315C49),
        ),
      );
    }
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
        actions: [
          if (widget.patients.length > 1 && (_page == 0 || _page == 1))
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: DropdownButton<int>(
                value: _selectedPatientId,
                underline: const SizedBox(),
                icon: const Icon(Icons.arrow_drop_down, color: Color(0xFF315C49)),
                items: widget.patients
                    .map((p) => DropdownMenuItem(
                          value: p.id,
                          child: Text(p.name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                        ))
                    .toList(),
                onChanged: (id) => setState(() => _selectedPatientId = id),
              ),
            ),
        ],
      ),
      body: IndexedStack(index: _page, children: [
        _todayPage(context),
        _schedulesPage(context),
        _comingSoon(context, Icons.history, 'Lịch sử', 'Danh sách lần uống sẽ xuất hiện khi engine lịch được triển khai.'),
        _comingSoon(context, Icons.notifications_none, 'Cảnh báo', 'Cảnh báo sẽ được phát triển ở giai đoạn sau.'),
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
    final currentPatient = widget.patients.where((p) => p.id == _selectedPatientId).firstOrNull ??
        (widget.patients.isNotEmpty ? widget.patients.first : null);

    // Lọc lịch theo bệnh nhân đang chọn
    final displayedSchedules = _selectedPatientId == null
        ? _localSchedules
        : _localSchedules.where((s) => s.patientId == _selectedPatientId).toList();

    return ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
      Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: colors.primary, borderRadius: BorderRadius.circular(22)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('CHĂM SÓC HÔM NAY', style: TextStyle(color: Colors.white70, fontSize: 11, letterSpacing: 1.3)),
          const SizedBox(height: 10),
          Text(currentPatient?.name ?? 'Chưa có hồ sơ', style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          const Text('Giờ demo: 07:59 · GMT+7', style: TextStyle(color: Colors.white70)),
          const SizedBox(height: 16),
          const Row(children: [Icon(Icons.info_outline, color: Color(0xFFD9E9A8), size: 17), SizedBox(width: 8), Expanded(child: Text('Chưa đến giờ uống theo lịch.', style: TextStyle(color: Colors.white, fontSize: 13)))]),
        ]),
      ),
      const SizedBox(height: 23),
      Text('Lịch uống trong ngày', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
      const SizedBox(height: 10),
      if (displayedSchedules.isEmpty)
        _emptyCard(context, 'Chưa có lịch uống. Hãy thêm lịch mới để bắt đầu.')
      else
        ...displayedSchedules.map((schedule) => _scheduleCard(context, schedule)),
      const SizedBox(height: 10),
      Text('Nhấn vào thẻ lịch để chỉnh sửa hoặc gạt công tắc để tạm dừng.', style: TextStyle(color: colors.onSurfaceVariant, fontSize: 12, height: 1.4)),
    ]);
  }

  Widget _schedulesPage(BuildContext context) {
    final displayedSchedules = _selectedPatientId == null
        ? _localSchedules
        : _localSchedules.where((s) => s.patientId == _selectedPatientId).toList();

    return ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 90), children: [
      Text('Lịch đã lưu', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
      const SizedBox(height: 6),
      Text('Gạt công tắc để bật/tắt. Nhấn vào thẻ để sửa tên thuốc, giờ hoặc ngăn.', style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant)),
      const SizedBox(height: 16),
      if (displayedSchedules.isEmpty)
        _emptyCard(context, 'Chưa có lịch. Nhấn “Thêm lịch” để tạo.')
      else
        ...displayedSchedules.map((schedule) => _scheduleCard(context, schedule)),
    ]);
  }

  // ==================== VIỆC 4: THẺ LỊCH VỚI TOGGLE SWITCH VÀ NÚT EDIT ====================
  Widget _scheduleCard(BuildContext context, MedicationSchedule schedule) {
    final patient = widget.patients.where((item) => item.id == schedule.patientId).firstOrNull;
    final isUpdating = _updatingScheduleIds.contains(schedule.id);

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => _showEditSchedule(schedule),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          child: Row(
            children: [
              CircleAvatar(
                backgroundColor: schedule.active ? const Color(0xFFE6ECDB) : const Color(0xFFEBEBEB),
                child: Text(
                  '${schedule.slot}',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: schedule.active ? const Color(0xFF315C49) : Colors.grey,
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      schedule.medicationName,
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 16,
                        decoration: schedule.active ? null : TextDecoration.lineThrough,
                        color: schedule.active ? null : Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${patient?.name ?? 'Hồ sơ'} · Ngăn ${schedule.slot} · ${schedule.active ? 'Đang bật' : 'Đang tạm dừng'}',
                      style: TextStyle(
                        fontSize: 12,
                        color: schedule.active ? Theme.of(context).colorScheme.onSurfaceVariant : Colors.grey,
                      ),
                    ),
                  ],
                ),
              ),
              Text(
                schedule.time,
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 16,
                  color: schedule.active ? null : Colors.grey,
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.edit_outlined, size: 20),
                tooltip: 'Sửa lịch',
                onPressed: () => _showEditSchedule(schedule),
              ),
              isUpdating
                  ? const SizedBox(
                      width: 32,
                      height: 32,
                      child: Padding(
                        padding: EdgeInsets.all(6),
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    )
                  : Switch(
                      value: schedule.active,
                      activeTrackColor: const Color(0xFF315C49),
                      onChanged: (newValue) => _toggleSchedule(schedule, newValue),
                    ),
            ],
          ),
        ),
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

// ==================== DIALOG CHỈNH SỬA LỊCH (ĐỘC LẬP & AN TOÀN LIFECYCLE) ====================
class _EditScheduleDialog extends StatefulWidget {
  const _EditScheduleDialog({
    required this.schedule,
    required this.patient,
    required this.onSubmit,
  });

  final MedicationSchedule schedule;
  final Patient? patient;
  final Future<void> Function(Map<String, dynamic> values) onSubmit;

  @override
  State<_EditScheduleDialog> createState() => _EditScheduleDialogState();
}

class _EditScheduleDialogState extends State<_EditScheduleDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late int _slot;
  late TimeOfDay _time;
  late bool _active;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.schedule.medicationName);
    _slot = widget.schedule.slot;
    _active = widget.schedule.active;

    final parts = widget.schedule.time.split(':');
    _time = TimeOfDay(
      hour: int.tryParse(parts.first) ?? 8,
      minute: parts.length > 1 ? (int.tryParse(parts[1]) ?? 0) : 0,
    );
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Chỉnh sửa lịch uống thuốc', style: TextStyle(fontWeight: FontWeight.w700)),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (widget.patient != null) ...[
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFFE6ECDB),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Row(children: [
                  const Icon(Icons.person_outline, size: 18, color: Color(0xFF315C49)),
                  const SizedBox(width: 8),
                  Text('Hồ sơ: ${widget.patient!.name}', style: const TextStyle(fontWeight: FontWeight.w600, color: Color(0xFF315C49))),
                ]),
              ),
              const SizedBox(height: 14),
            ],
            TextFormField(
              controller: _nameController,
              decoration: const InputDecoration(labelText: 'Tên thuốc'),
              validator: (value) => value == null || value.trim().isEmpty ? 'Nhập tên thuốc' : null,
            ),
            const SizedBox(height: 14),
            const Text('Ngăn thuốc:', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            SizedBox(
              width: double.infinity,
              child: SegmentedButton<int>(
                segments: const [
                  ButtonSegment(value: 1, label: Text('Ngăn 1')),
                  ButtonSegment(value: 2, label: Text('Ngăn 2')),
                  ButtonSegment(value: 3, label: Text('Ngăn 3')),
                ],
                selected: {_slot},
                onSelectionChanged: (newSet) => setState(() => _slot = newSet.first),
              ),
            ),
            const SizedBox(height: 14),
            OutlinedButton.icon(
              onPressed: () async {
                final chosen = await showTimePicker(
                  context: context,
                  initialTime: _time,
                  initialEntryMode: TimePickerEntryMode.input,
                  helpText: 'Nhập giờ uống thuốc (24h)',
                  hourLabelText: 'Giờ',
                  minuteLabelText: 'Phút',
                  cancelText: 'Hủy',
                  confirmText: 'Xong',
                  errorInvalidText: 'Giờ không hợp lệ',
                  builder: (context, child) => MediaQuery(
                    data: MediaQuery.of(context).copyWith(alwaysUse24HourFormat: true),
                    child: child!,
                  ),
                );
                if (chosen != null) setState(() => _time = chosen);
              },
              icon: const Icon(Icons.schedule),
              label: Text('Giờ uống: ${_time.hour.toString().padLeft(2, '0')}:${_time.minute.toString().padLeft(2, '0')} (Bấm để đổi)'),
            ),
            const SizedBox(height: 12),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Bật lịch này'),
              subtitle: Text(_active ? 'Đang kích hoạt nhắc nhở' : 'Đang tạm dừng', style: const TextStyle(fontSize: 12)),
              value: _active,
              onChanged: (val) => setState(() => _active = val),
            ),
            if (_error != null) ...[
              const SizedBox(height: 10),
              Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error, fontSize: 13)),
            ],
          ]),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _busy ? null : () => Navigator.of(context).pop(false),
          child: const Text('Hủy'),
        ),
        FilledButton(
          onPressed: _busy
              ? null
              : () async {
                  if (!_formKey.currentState!.validate()) return;
                  setState(() {
                    _busy = true;
                    _error = null;
                  });
                  final nav = Navigator.of(context);
                  final formattedTime = '${_time.hour.toString().padLeft(2, '0')}:${_time.minute.toString().padLeft(2, '0')}';
                  try {
                    await widget.onSubmit({
                      'medication_name': _nameController.text.trim(),
                      'slot': _slot,
                      'time': formattedTime,
                      'active': _active,
                    });
                    nav.pop(true);
                  } catch (exception) {
                    if (mounted) {
                      setState(() {
                        _busy = false;
                        _error = exception.toString();
                      });
                    }
                  }
                },
          child: _busy
              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
              : const Text('Lưu thay đổi'),
        ),
      ],
    );
  }
}

// ==================== DIALOG TẠO LỊCH (ĐỘC LẬP & AN TOÀN LIFECYCLE) ====================
class _CreateScheduleDialog extends StatefulWidget {
  const _CreateScheduleDialog({
    required this.patients,
    required this.initialPatientId,
    required this.onSubmit,
  });

  final List<Patient> patients;
  final int initialPatientId;
  final Future<void> Function(Map<String, dynamic> values) onSubmit;

  @override
  State<_CreateScheduleDialog> createState() => _CreateScheduleDialogState();
}

class _CreateScheduleDialogState extends State<_CreateScheduleDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late int _patientId;
  int _slot = 1;
  TimeOfDay _time = const TimeOfDay(hour: 8, minute: 0);
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController();
    _patientId = widget.initialPatientId;
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final patient = widget.patients.where((p) => p.id == _patientId).firstOrNull;

    return AlertDialog(
      title: const Text('Thêm lịch uống thuốc'),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (widget.patients.length > 1)
              DropdownButtonFormField<int>(
                initialValue: _patientId,
                decoration: const InputDecoration(labelText: 'Người được chăm sóc'),
                items: widget.patients.map((p) => DropdownMenuItem(value: p.id, child: Text(p.name))).toList(),
                onChanged: (value) => setState(() => _patientId = value ?? _patientId),
              )
            else if (patient != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFFE6ECDB),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Row(children: [
                  const Icon(Icons.person_outline, size: 18, color: Color(0xFF315C49)),
                  const SizedBox(width: 8),
                  Text('Hồ sơ: ${patient.name}', style: const TextStyle(fontWeight: FontWeight.w600, color: Color(0xFF315C49))),
                ]),
              ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _nameController,
              decoration: const InputDecoration(labelText: 'Tên thuốc mẫu'),
              validator: (value) => value == null || value.trim().isEmpty ? 'Nhập tên thuốc' : null,
            ),
            const SizedBox(height: 14),
            const Text('Ngăn thuốc:', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            SizedBox(
              width: double.infinity,
              child: SegmentedButton<int>(
                segments: const [
                  ButtonSegment(value: 1, label: Text('Ngăn 1')),
                  ButtonSegment(value: 2, label: Text('Ngăn 2')),
                  ButtonSegment(value: 3, label: Text('Ngăn 3')),
                ],
                selected: {_slot},
                onSelectionChanged: (newSet) => setState(() => _slot = newSet.first),
              ),
            ),
            const SizedBox(height: 14),
            OutlinedButton.icon(
              onPressed: () async {
                final chosen = await showTimePicker(
                  context: context,
                  initialTime: _time,
                  initialEntryMode: TimePickerEntryMode.input,
                  helpText: 'Nhập giờ uống thuốc (24h)',
                  hourLabelText: 'Giờ',
                  minuteLabelText: 'Phút',
                  cancelText: 'Hủy',
                  confirmText: 'Xong',
                  errorInvalidText: 'Giờ không hợp lệ',
                  builder: (context, child) => MediaQuery(
                    data: MediaQuery.of(context).copyWith(alwaysUse24HourFormat: true),
                    child: child!,
                  ),
                );
                if (chosen != null) setState(() => _time = chosen);
              },
              icon: const Icon(Icons.schedule),
              label: Text('Giờ uống: ${_time.hour.toString().padLeft(2, '0')}:${_time.minute.toString().padLeft(2, '0')} (Bấm để đổi)'),
            ),
            if (_error != null) ...[
              const SizedBox(height: 10),
              Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error, fontSize: 13)),
            ],
          ]),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _busy ? null : () => Navigator.of(context).pop(false),
          child: const Text('Hủy'),
        ),
        FilledButton(
          onPressed: _busy
              ? null
              : () async {
                  if (!_formKey.currentState!.validate()) return;
                  setState(() {
                    _busy = true;
                    _error = null;
                  });
                  final nav = Navigator.of(context);
                  final formattedTime = '${_time.hour.toString().padLeft(2, '0')}:${_time.minute.toString().padLeft(2, '0')}';
                  try {
                    await widget.onSubmit({
                      'patient_id': _patientId,
                      'medication_name': _nameController.text.trim(),
                      'slot': _slot,
                      'time': formattedTime,
                    });
                    nav.pop(true);
                  } catch (exception) {
                    if (mounted) {
                      setState(() {
                        _busy = false;
                        _error = exception.toString();
                      });
                    }
                  }
                },
          child: _busy
              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
              : const Text('Lưu lịch'),
        ),
      ],
    );
  }
}
