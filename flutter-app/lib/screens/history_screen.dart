import 'package:flutter/material.dart';

import '../api/smart_pill_api.dart';
import '../models.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({
    super.key,
    this.api,
    this.initialEvents,
  });

  final SmartPillApi? api;
  final List<DeviceEventItem>? initialEvents;

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<DeviceEventItem> _events = [];
  bool _loading = false;
  String? _error;
  int? _selectedSlot;
  String? _selectedDate;

  @override
  void initState() {
    super.initState();
    if (widget.initialEvents != null) {
      _events = widget.initialEvents!;
    } else if (widget.api?.token != null) {
      _loadEvents();
    }
  }

  Future<void> _loadEvents() async {
    final api = widget.api;
    if (api == null || api.token == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await api.events(
        slot: _selectedSlot,
        date: _selectedDate,
      );
      if (!mounted) return;
      setState(() {
        _events = items;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final initial = _selectedDate != null
        ? (DateTime.tryParse(_selectedDate!) ?? now)
        : DateTime(2026, 10, 9);
    final chosen = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2024, 1, 1),
      lastDate: DateTime(2030, 12, 31),
    );
    if (chosen == null || !mounted) return;
    final formatted =
        '${chosen.year.toString().padLeft(4, '0')}-${chosen.month.toString().padLeft(2, '0')}-${chosen.day.toString().padLeft(2, '0')}';
    setState(() => _selectedDate = formatted);
    await _loadEvents();
  }

  List<DeviceEventItem> get _filteredEvents {
    return _events.where((event) {
      if (_selectedSlot != null && event.slot != _selectedSlot) {
        return false;
      }
      if (_selectedDate != null &&
          _selectedDate!.isNotEmpty &&
          event.dateKey != _selectedDate) {
        return false;
      }
      return true;
    }).toList();
  }

  String _eventTitle(String eventType) {
    switch (eventType) {
      case 'LID_OPENED':
        return 'Mở nắp ngăn thuốc';
      case 'LID_CLOSED':
        return 'Đóng nắp ngăn thuốc';
      case 'PILL_REMOVED':
      case 'PILL_DISPENSED':
        return 'Lấy viên thuốc khỏi ngăn';
      case 'WEIGHT_READING':
      case 'WEIGHT_SAMPLE':
      case 'WEIGHT_CHANGED':
        return 'Đọc cảm biến trọng lượng';
      case 'CONFIRM_PRESSED':
      case 'DOSE_CONFIRMED':
      case 'CONFIRMED':
        return 'Đã xác nhận uống thuốc';
      case 'REMINDER_SENT':
        return 'Phát tín hiệu nhắc uống thuốc';
      case 'ALERT_CREATED':
        return 'Tạo cảnh báo quá hạn';
      case 'CLOCK_ADVANCED':
        return 'Tiến đồng hồ mô phỏng';
      case 'SIMULATION_RESET':
        return 'Đặt lại trạng thái demo';
      default:
        return eventType;
    }
  }

  IconData _eventIcon(String eventType) {
    switch (eventType) {
      case 'CONFIRM_PRESSED':
      case 'DOSE_CONFIRMED':
      case 'CONFIRMED':
        return Icons.check_circle_outline;
      case 'ALERT_CREATED':
        return Icons.warning_amber_rounded;
      case 'LID_OPENED':
      case 'LID_CLOSED':
        return Icons.inventory_2_outlined;
      case 'PILL_REMOVED':
      case 'PILL_DISPENSED':
        return Icons.medication_outlined;
      default:
        return Icons.history;
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final filtered = _filteredEvents;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Lịch sử sự kiện',
                    style: Theme.of(context)
                        .textTheme
                        .titleLarge
                        ?.copyWith(fontWeight: FontWeight.w600),
                  ),
                  IconButton(
                    onPressed: _loading ? null : _loadEvents,
                    tooltip: 'Làm mới lịch sử',
                    icon: const Icon(Icons.refresh),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    FilterChip(
                      label: const Text('Tất cả ngăn'),
                      selected: _selectedSlot == null,
                      onSelected: (_) {
                        setState(() => _selectedSlot = null);
                        _loadEvents();
                      },
                    ),
                    const SizedBox(width: 8),
                    for (final slot in [1, 2, 3]) ...[
                      FilterChip(
                        label: Text('Ngăn $slot'),
                        selected: _selectedSlot == slot,
                        onSelected: (_) {
                          setState(() => _selectedSlot =
                              _selectedSlot == slot ? null : slot);
                          _loadEvents();
                        },
                      ),
                      const SizedBox(width: 8),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  OutlinedButton.icon(
                    onPressed: _pickDate,
                    icon: const Icon(Icons.calendar_today, size: 16),
                    label: Text(
                      _selectedDate == null
                          ? 'Lọc theo ngày: Tất cả'
                          : 'Ngày: $_selectedDate',
                    ),
                  ),
                  if (_selectedDate != null) ...[
                    const SizedBox(width: 8),
                    TextButton.icon(
                      onPressed: () {
                        setState(() => _selectedDate = null);
                        _loadEvents();
                      },
                      icon: const Icon(Icons.clear, size: 16),
                      label: const Text('Xóa ngày'),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _error != null
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.error_outline,
                                size: 40, color: colors.error),
                            const SizedBox(height: 12),
                            Text(
                              _error!,
                              textAlign: TextAlign.center,
                              style: TextStyle(color: colors.error),
                            ),
                            const SizedBox(height: 12),
                            OutlinedButton.icon(
                              onPressed: _loadEvents,
                              icon: const Icon(Icons.refresh),
                              label: const Text('Thử lại'),
                            ),
                          ],
                        ),
                      ),
                    )
                  : filtered.isEmpty
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(24),
                            child: Text(
                              'Chưa có sự kiện nào phù hợp với bộ lọc.',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: colors.onSurfaceVariant),
                            ),
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: _loadEvents,
                          child: ListView.builder(
                            padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
                            itemCount: filtered.length,
                            itemBuilder: (context, index) {
                              final event = filtered[index];
                              final slotLabel = event.slot != null
                                  ? 'Ngăn ${event.slot}'
                                  : 'Hệ thống';
                              return Card(
                                margin: const EdgeInsets.only(bottom: 10),
                                child: ListTile(
                                  leading: CircleAvatar(
                                    backgroundColor: const Color(0xFFE6ECDB),
                                    child: Icon(
                                      _eventIcon(event.eventType),
                                      color: colors.primary,
                                    ),
                                  ),
                                  title: Text(
                                    _eventTitle(event.eventType),
                                    style: const TextStyle(
                                        fontWeight: FontWeight.w600),
                                  ),
                                  subtitle: Text(
                                    '$slotLabel · Ngày: ${event.dateKey}\nThời gian: ${event.timestamp}',
                                  ),
                                  isThreeLine: true,
                                ),
                              );
                            },
                          ),
                        ),
        ),
      ],
    );
  }
}
