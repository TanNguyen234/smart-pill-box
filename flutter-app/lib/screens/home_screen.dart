import 'dart:async';
import 'package:flutter/material.dart';

import '../api/smart_pill_api.dart';
import '../models.dart';
import 'alerts_screen.dart';
import 'history_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    required this.account,
    required this.patients,
    required this.schedules,
    required this.onLogout,
    required this.onCreateSchedule,
    required this.onUpdateSchedule,
    required this.api,
    this.onRefreshData,
  });

  final Account account;
  final List<Patient> patients;
  final List<MedicationSchedule> schedules;
  final VoidCallback onLogout;
  final Future<void> Function(Map<String, dynamic> values) onCreateSchedule;
  final Future<void> Function(int scheduleId, Map<String, dynamic> values) onUpdateSchedule;
  final SmartPillApi api;
  final Future<void> Function()? onRefreshData;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _page = 0;
  int? _selectedPatientId;
  List<DoseItem> _todayDoses = [];
  int _pendingAlertCount = 0;
  bool _loadingDoses = false;
  Timer? _pollingTimer;

  @override
  void initState() {
    super.initState();
    if (widget.patients.isNotEmpty) {
      _selectedPatientId = widget.patients.first.id;
    }
    _fetchTodayData();
    // Tự động làm mới mỗi 3 giây để đồng bộ tức thời với Web Simulator
    _pollingTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      if (mounted) {
        _fetchTodayData(silent: true);
      }
    });
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchTodayData({bool silent = false}) async {
    if (!silent) {
      setState(() => _loadingDoses = true);
    }
    try {
      final doses = await widget.api.doses(patientId: _selectedPatientId);
      final alerts = await widget.api.alerts(status: 'PENDING');
      if (mounted) {
        setState(() {
          _todayDoses = doses;
          _pendingAlertCount = alerts.length;
          _loadingDoses = false;
        });
      }
    } catch (_) {
      if (mounted && !silent) {
        setState(() => _loadingDoses = false);
      }
    }
  }

  Future<void> _handleRefreshAll() async {
    if (widget.onRefreshData != null) {
      await widget.onRefreshData!();
    }
    await _fetchTodayData();
  }

  Future<void> _showCreateSchedule() async {
    final created = await showDialog<bool>(
      context: context,
      builder: (_) => _CreateScheduleDialog(
        patients: widget.patients,
        initialPatientId: _selectedPatientId ?? (widget.patients.isNotEmpty ? widget.patients.first.id : 1),
        onSubmit: widget.onCreateSchedule,
      ),
    );
    if (created == true && mounted) {
      await _handleRefreshAll();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã thêm lịch uống thuốc thành công')),
      );
    }
  }

  Future<void> _showEditSchedule(MedicationSchedule schedule) async {
    final updated = await showDialog<bool>(
      context: context,
      builder: (_) => _EditScheduleDialog(
        schedule: schedule,
        onSubmit: (values) => widget.onUpdateSchedule(schedule.id, values),
      ),
    );
    if (updated == true && mounted) {
      await _handleRefreshAll();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã cập nhật lịch uống thuốc thành công')),
      );
    }
  }

  Future<void> _toggleSchedule(MedicationSchedule schedule, bool value) async {
    final originalState = schedule.active;
    setState(() {
      final idx = widget.schedules.indexWhere((s) => s.id == schedule.id);
      if (idx != -1) {
        widget.schedules[idx] = schedule.copyWith(active: value);
      }
    });

    try {
      await widget.onUpdateSchedule(schedule.id, {'active': value});
      if (widget.onRefreshData != null) {
        await widget.onRefreshData!();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          final idx = widget.schedules.indexWhere((s) => s.id == schedule.id);
          if (idx != -1) {
            widget.schedules[idx] = schedule.copyWith(active: originalState);
          }
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Không thể cập nhật trạng thái lịch: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final titles = ['Hôm nay', 'Lịch uống', 'Lịch sử', 'Cảnh báo', 'Tài khoản'];

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'SMART PILL BOX',
              style: TextStyle(fontSize: 12, letterSpacing: 1.4, fontWeight: FontWeight.w700),
            ),
            Text(
              titles[_page],
              style: TextStyle(fontSize: 12, color: colors.onSurfaceVariant, fontWeight: FontWeight.normal),
            ),
          ],
        ),
        actions: [
          IconButton(
            onPressed: _handleRefreshAll,
            tooltip: 'Tải lại dữ liệu',
            icon: const Icon(Icons.refresh),
          ),
        ],
        backgroundColor: const Color(0xFFF5F4EE),
      ),
      body: IndexedStack(
        index: _page,
        children: [
          _todayPage(context),
          _schedulesPage(context),
          HistoryScreen(api: widget.api),
          AlertsScreen(api: widget.api),
          _accountPage(context),
        ],
      ),
      floatingActionButton: _page == 1
          ? FloatingActionButton.extended(
              onPressed: _showCreateSchedule,
              icon: const Icon(Icons.add),
              label: const Text('Thêm lịch'),
            )
          : null,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _page,
        onDestinationSelected: (index) {
          setState(() => _page = index);
          if (index == 0) _fetchTodayData();
        },
        destinations: [
          const NavigationDestination(
            icon: Icon(Icons.today_outlined),
            selectedIcon: Icon(Icons.today),
            label: 'Hôm nay',
          ),
          const NavigationDestination(
            icon: Icon(Icons.calendar_month_outlined),
            selectedIcon: Icon(Icons.calendar_month),
            label: 'Lịch',
          ),
          const NavigationDestination(
            icon: Icon(Icons.history),
            label: 'Lịch sử',
          ),
          NavigationDestination(
            icon: Badge(
              isLabelVisible: _pendingAlertCount > 0,
              label: Text('$_pendingAlertCount'),
              child: const Icon(Icons.notifications_none),
            ),
            selectedIcon: Badge(
              isLabelVisible: _pendingAlertCount > 0,
              label: Text('$_pendingAlertCount'),
              child: const Icon(Icons.notifications),
            ),
            label: 'Cảnh báo',
          ),
          const NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Tài khoản',
          ),
        ],
      ),
    );
  }

  String _doseStatusLabel(String status) {
    switch (status.toLowerCase()) {
      case 'pending':
        return 'Đang nhắc uống';
      case 'reminded':
        return 'Đã nhắc lại (2 phút)';
      case 'overdue':
        return 'Quá hạn, chưa xác nhận';
      case 'confirmed_on_time':
        return 'Đã xác nhận đúng hạn';
      case 'confirmed_late':
        return 'Đã xác nhận trễ';
      default:
        return 'Chưa đến giờ';
    }
  }

  Color _slotColor(int slot) {
    switch (slot) {
      case 1:
        return const Color(0xFF0284C7);
      case 2:
        return const Color(0xFFEA580C);
      case 3:
        return const Color(0xFF059669);
      default:
        return const Color(0xFF0D9488);
    }
  }

  IconData _doseStatusIcon(String status) {
    switch (status.toLowerCase()) {
      case 'pending':
        return Icons.notifications_active_outlined;
      case 'reminded':
        return Icons.warning_amber_rounded;
      case 'overdue':
        return Icons.error_outline;
      case 'confirmed_on_time':
      case 'confirmed_late':
        return Icons.check_circle_outline;
      default:
        return Icons.schedule;
    }
  }

  Color _doseStatusColor(BuildContext context, String status) {
    switch (status.toLowerCase()) {
      case 'pending':
        return const Color(0xFFEA580C);
      case 'reminded':
        return Colors.deepOrange;
      case 'overdue':
        return const Color(0xFFDC2626);
      case 'confirmed_on_time':
        return const Color(0xFF059669);
      case 'confirmed_late':
        return const Color(0xFFD97706);
      default:
        return const Color(0xFF64748B);
    }
  }

  Widget _todayPage(BuildContext context) {
    final currentPatient = widget.patients.where((p) => p.id == _selectedPatientId).firstOrNull ??
        (widget.patients.isNotEmpty ? widget.patients.first : null);

    final filteredSchedules = widget.schedules
        .where((s) => _selectedPatientId == null || s.patientId == _selectedPatientId)
        .toList();

    return RefreshIndicator(
      onRefresh: _handleRefreshAll,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        children: [
          Container(
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF0F766E), Color(0xFF134E4A)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(24),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF0D9488).withValues(alpha: 0.28),
                  blurRadius: 22,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.health_and_safety_outlined, size: 14, color: Color(0xFF5EEAD4)),
                          SizedBox(width: 6),
                          Text(
                            'CHĂM SÓC HÔM NAY',
                            style: TextStyle(color: Colors.white, fontSize: 11, letterSpacing: 1.1, fontWeight: FontWeight.w700),
                          ),
                        ],
                      ),
                    ),
                    if (widget.patients.length > 1)
                      DropdownButton<int>(
                        value: _selectedPatientId,
                        dropdownColor: const Color(0xFF0F766E),
                        underline: const SizedBox(),
                        icon: const Icon(Icons.arrow_drop_down, color: Colors.white),
                        items: widget.patients.map((p) {
                          return DropdownMenuItem(
                            value: p.id,
                            child: Text(p.name, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                          );
                        }).toList(),
                        onChanged: (val) {
                          setState(() => _selectedPatientId = val);
                          _fetchTodayData();
                        },
                      ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(
                  currentPatient?.name ?? 'Chưa có hồ sơ',
                  style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w800, letterSpacing: -0.3),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: const BoxDecoration(color: Color(0xFF34D399), shape: BoxShape.circle),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      _todayDoses.isNotEmpty
                          ? 'Mốc nhắc gần nhất: ${_todayDoses.first.scheduledAt}'
                          : 'Đồng bộ trực tiếp với máy chủ',
                      style: const TextStyle(color: Color(0xFFCCFBF1), fontSize: 13, fontWeight: FontWeight.w500),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                if (_pendingAlertCount > 0)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: const Color(0xFFB91C1C),
                      borderRadius: BorderRadius.circular(14),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.2),
                          blurRadius: 8,
                          offset: const Offset(0, 3),
                        ),
                      ],
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.warning_amber_rounded, color: Colors.white, size: 20),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            'Có $_pendingAlertCount cảnh báo quá hạn cần kiểm tra!',
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 13),
                          ),
                        ),
                      ],
                    ),
                  )
                else
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Row(
                      children: [
                        Icon(Icons.check_circle_outline, color: Color(0xFF5EEAD4), size: 18),
                        SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            'Không có cảnh báo quá hạn nào.',
                            style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w500),
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 26),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Lịch uống hôm nay',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: Color(0xFF0F172A), letterSpacing: -0.2),
              ),
              if (_loadingDoses)
                const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF0D9488))),
            ],
          ),
          const SizedBox(height: 12),
          if (filteredSchedules.isEmpty)
            _emptyCard(context, 'Chưa có lịch uống nào cho hồ sơ này.')
          else
            ...filteredSchedules.map((schedule) {
              final dose = _todayDoses.where((d) => d.scheduleId == schedule.id).firstOrNull;
              final status = dose?.status ?? 'scheduled';
              final statusText = _doseStatusLabel(status);
              final statusColor = _doseStatusColor(context, status);
              final statusIcon = _doseStatusIcon(status);
              final slotColor = _slotColor(schedule.slot);

              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Container(
                        width: 46,
                        height: 46,
                        decoration: BoxDecoration(
                          color: slotColor.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        alignment: Alignment.center,
                        child: Text(
                          '${schedule.slot}',
                          style: TextStyle(fontWeight: FontWeight.w800, color: slotColor, fontSize: 18),
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              schedule.medicationName,
                              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: Color(0xFF0F172A)),
                            ),
                            const SizedBox(height: 5),
                            Row(
                              children: [
                                const Icon(Icons.access_time_rounded, size: 14, color: Color(0xFF64748B)),
                                const SizedBox(width: 4),
                                Text(
                                  'Ngăn ${schedule.slot} · Giờ uống: ${schedule.time}',
                                  style: const TextStyle(color: Color(0xFF64748B), fontSize: 13, fontWeight: FontWeight.w500),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: statusColor.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: statusColor.withValues(alpha: 0.2)),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(statusIcon, size: 14, color: statusColor),
                                  const SizedBox(width: 5),
                                  Text(
                                    statusText,
                                    style: TextStyle(
                                      color: statusColor,
                                      fontWeight: FontWeight.w700,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.edit_outlined, color: Color(0xFF64748B)),
                        tooltip: 'Chỉnh sửa lịch',
                        onPressed: () => _showEditSchedule(schedule),
                      ),
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget _schedulesPage(BuildContext context) {
    final filteredSchedules = widget.schedules
        .where((s) => _selectedPatientId == null || s.patientId == _selectedPatientId)
        .toList();

    return RefreshIndicator(
      onRefresh: _handleRefreshAll,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 90),
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Quản lý lịch uống',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: Color(0xFF0F172A)),
              ),
              if (widget.patients.length > 1)
                DropdownButton<int>(
                  value: _selectedPatientId,
                  hint: const Text('Tất cả'),
                  items: [
                    const DropdownMenuItem(value: null, child: Text('Tất cả hồ sơ')),
                    ...widget.patients.map((p) => DropdownMenuItem(value: p.id, child: Text(p.name))),
                  ],
                  onChanged: (val) => setState(() => _selectedPatientId = val),
                ),
            ],
          ),
          const SizedBox(height: 6),
          const Text(
            'Bật/tắt công tắc hoặc bấm vào biểu tượng bút để chỉnh sửa.',
            style: TextStyle(color: Color(0xFF64748B), fontSize: 13),
          ),
          const SizedBox(height: 16),
          if (filteredSchedules.isEmpty)
            _emptyCard(context, 'Chưa có lịch. Nhấn “Thêm lịch” bên dưới để tạo.')
          else
            ...filteredSchedules.map((schedule) {
              final patient = widget.patients.where((p) => p.id == schedule.patientId).firstOrNull;
              final slotColor = _slotColor(schedule.slot);
              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  child: Row(
                    children: [
                      Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          color: slotColor.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        alignment: Alignment.center,
                        child: Text(
                          '${schedule.slot}',
                          style: TextStyle(fontWeight: FontWeight.w800, color: slotColor, fontSize: 17),
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(schedule.medicationName,
                                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: Color(0xFF0F172A))),
                            const SizedBox(height: 4),
                            Text(
                              '${patient?.name ?? 'Hồ sơ'} · Ngăn ${schedule.slot} · ${schedule.time}',
                              style: const TextStyle(color: Color(0xFF64748B), fontSize: 13),
                            ),
                          ],
                        ),
                      ),
                      Switch(
                        activeTrackColor: const Color(0xFF0D9488),
                        value: schedule.active,
                        onChanged: (val) => _toggleSchedule(schedule, val),
                      ),
                      IconButton(
                        icon: const Icon(Icons.edit_outlined, color: Color(0xFF64748B)),
                        tooltip: 'Chỉnh sửa lịch',
                        onPressed: () => _showEditSchedule(schedule),
                      ),
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget _accountPage(BuildContext context) => ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Row(
                children: [
                  Container(
                    width: 52,
                    height: 52,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF0F766E), Color(0xFF14B8A6)],
                      ),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    alignment: Alignment.center,
                    child: const Icon(Icons.person, color: Colors.white, size: 28),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(widget.account.displayName,
                            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17, color: Color(0xFF0F172A))),
                        const SizedBox(height: 2),
                        Text(widget.account.email, style: const TextStyle(color: Color(0xFF64748B), fontSize: 13)),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFFCCFBF1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      widget.account.role,
                      style: const TextStyle(color: Color(0xFF0F766E), fontWeight: FontWeight.w700, fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              leading: Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: const Color(0xFFF1F5F9), borderRadius: BorderRadius.circular(10)),
                child: const Icon(Icons.devices_other_outlined, color: Color(0xFF0F766E)),
              ),
              title: const Text('Thiết bị Smart Pill Box', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: const Text('Mã máy: SIM-001 • Đang kết nối trực tuyến'),
              trailing: Container(
                width: 10,
                height: 10,
                decoration: const BoxDecoration(color: Color(0xFF10B981), shape: BoxShape.circle),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              leading: Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: const Color(0xFFF1F5F9), borderRadius: BorderRadius.circular(10)),
                child: const Icon(Icons.people_outline, color: Color(0xFF0F766E)),
              ),
              title: const Text('Hồ sơ được chăm sóc', style: TextStyle(fontWeight: FontWeight.w700)),
              trailing: Text('${widget.patients.length}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            ),
          ),
          const SizedBox(height: 24),
          SizedBox(
            height: 48,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFFDC2626),
                side: const BorderSide(color: Color(0xFFFECACA)),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              ),
              onPressed: widget.onLogout,
              icon: const Icon(Icons.logout),
              label: const Text('Đăng xuất', style: TextStyle(fontWeight: FontWeight.w700)),
            ),
          ),
        ],
      );

  Widget _emptyCard(BuildContext context, String message) => Card(
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Text(message, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant)),
        ),
      );
}

// ==================== DIALOG SỬA LỊCH ====================
class _EditScheduleDialog extends StatefulWidget {
  const _EditScheduleDialog({
    required this.schedule,
    required this.onSubmit,
  });

  final MedicationSchedule schedule;
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
    final parts = widget.schedule.time.split(':');
    final h = parts.isNotEmpty ? int.tryParse(parts[0]) ?? 8 : 8;
    final m = parts.length > 1 ? int.tryParse(parts[1]) ?? 0 : 0;
    _time = TimeOfDay(hour: h, minute: m);
    _active = widget.schedule.active;
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Chỉnh sửa lịch uống thuốc'),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(labelText: 'Tên thuốc'),
                validator: (val) => val == null || val.trim().isEmpty ? 'Nhập tên thuốc' : null,
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
                    builder: (context, child) => MediaQuery(
                      data: MediaQuery.of(context).copyWith(alwaysUse24HourFormat: true),
                      child: child!,
                    ),
                  );
                  if (chosen != null) setState(() => _time = chosen);
                },
                icon: const Icon(Icons.schedule),
                label: Text(
                  'Giờ uống: ${_time.hour.toString().padLeft(2, '0')}:${_time.minute.toString().padLeft(2, '0')} (Bấm để đổi)',
                ),
              ),
              const SizedBox(height: 14),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Kích hoạt lịch này'),
                value: _active,
                onChanged: (val) => setState(() => _active = val),
              ),
              if (_error != null) ...[
                const SizedBox(height: 10),
                Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error, fontSize: 13)),
              ],
            ],
          ),
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
                  final formattedTime =
                      '${_time.hour.toString().padLeft(2, '0')}:${_time.minute.toString().padLeft(2, '0')}';
                  try {
                    await widget.onSubmit({
                      'medication_name': _nameController.text.trim(),
                      'slot': _slot,
                      'time': formattedTime,
                      'active': _active,
                    });
                    if (context.mounted) Navigator.of(context).pop(true);
                  } catch (e) {
                    if (mounted) {
                      setState(() {
                        _busy = false;
                        _error = e.toString();
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

// ==================== DIALOG TẠO LỊCH ====================
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
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (widget.patients.length > 1)
                DropdownButtonFormField<int>(
                  initialValue: _patientId,
                  decoration: const InputDecoration(labelText: 'Người được chăm sóc'),
                  items: widget.patients.map((p) => DropdownMenuItem(value: p.id, child: Text(p.name))).toList(),
                  onChanged: (val) => setState(() => _patientId = val ?? _patientId),
                )
              else if (patient != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: const Color(0xFFE6ECDB),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.person_outline, size: 18, color: Color(0xFF315C49)),
                      const SizedBox(width: 8),
                      Text('Hồ sơ: ${patient.name}',
                          style: const TextStyle(fontWeight: FontWeight.w600, color: Color(0xFF315C49))),
                    ],
                  ),
                ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _nameController,
                decoration: const InputDecoration(labelText: 'Tên thuốc mẫu'),
                validator: (val) => val == null || val.trim().isEmpty ? 'Nhập tên thuốc' : null,
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
                    builder: (context, child) => MediaQuery(
                      data: MediaQuery.of(context).copyWith(alwaysUse24HourFormat: true),
                      child: child!,
                    ),
                  );
                  if (chosen != null) setState(() => _time = chosen);
                },
                icon: const Icon(Icons.schedule),
                label: Text(
                  'Giờ uống: ${_time.hour.toString().padLeft(2, '0')}:${_time.minute.toString().padLeft(2, '0')} (Bấm để đổi)',
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 10),
                Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error, fontSize: 13)),
              ],
            ],
          ),
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
                  final formattedTime =
                      '${_time.hour.toString().padLeft(2, '0')}:${_time.minute.toString().padLeft(2, '0')}';
                  try {
                    await widget.onSubmit({
                      'patient_id': _patientId,
                      'medication_name': _nameController.text.trim(),
                      'slot': _slot,
                      'time': formattedTime,
                    });
                    if (context.mounted) Navigator.of(context).pop(true);
                  } catch (e) {
                    if (mounted) {
                      setState(() {
                        _busy = false;
                        _error = e.toString();
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
