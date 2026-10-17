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

  Color _slotColor(int? slot) {
    switch (slot) {
      case 1:
        return const Color(0xFF0284C7); // Sky/Blue
      case 2:
        return const Color(0xFFEA580C); // Warm Orange
      case 3:
        return const Color(0xFF059669); // Emerald
      default:
        return const Color(0xFF64748B); // Slate
    }
  }

  Color _eventColor(String eventType) {
    switch (eventType) {
      case 'CONFIRM_PRESSED':
      case 'DOSE_CONFIRMED':
      case 'CONFIRMED':
        return const Color(0xFF059669);
      case 'ALERT_CREATED':
        return const Color(0xFFE11D48);
      case 'REMINDER_SENT':
        return const Color(0xFFD97706);
      case 'PILL_REMOVED':
      case 'PILL_DISPENSED':
        return const Color(0xFF7C3AED);
      case 'WEIGHT_READING':
      case 'WEIGHT_SAMPLE':
      case 'WEIGHT_CHANGED':
        return const Color(0xFF2563EB);
      case 'LID_OPENED':
        return const Color(0xFF0D9488);
      case 'LID_CLOSED':
        return const Color(0xFF64748B);
      case 'CLOCK_ADVANCED':
        return const Color(0xFF0891B2);
      default:
        return const Color(0xFF475569);
    }
  }

  String _formatTimestamp(String ts) {
    try {
      final parsed = DateTime.tryParse(ts);
      if (parsed != null) {
        final h = parsed.hour.toString().padLeft(2, '0');
        final m = parsed.minute.toString().padLeft(2, '0');
        final s = parsed.second.toString().padLeft(2, '0');
        return '$h:$m:$s';
      }
    } catch (_) {}
    if (ts.contains('T')) {
      final part = ts.split('T').last;
      return part.length >= 8 ? part.substring(0, 8) : part;
    }
    return ts;
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final filtered = _filteredEvents;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Header & Filters
        Container(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
          decoration: BoxDecoration(
            color: Colors.white,
            border: Border(
              bottom: BorderSide(
                color: colors.outlineVariant.withValues(alpha: 0.3),
              ),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Lịch sử sự kiện',
                        style: Theme.of(context)
                            .textTheme
                            .titleLarge
                            ?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: const Color(0xFF0F172A),
                            ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Nhật ký vận hành & cảm biến hộp SIM-001',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: const Color(0xFF64748B),
                            ),
                      ),
                    ],
                  ),
                  IconButton.filledTonal(
                    onPressed: _loading ? null : _loadEvents,
                    tooltip: 'Làm mới lịch sử',
                    icon: _loading
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.refresh_rounded, size: 20),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              // Slot Filter Chips
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
                      avatar: _selectedSlot == null
                          ? const Icon(Icons.check, size: 16)
                          : null,
                    ),
                    const SizedBox(width: 8),
                    for (final slot in [1, 2, 3]) ...[
                      FilterChip(
                        label: Text('Ngăn $slot'),
                        selected: _selectedSlot == slot,
                        selectedColor: _slotColor(slot).withValues(alpha: 0.18),
                        side: BorderSide(
                          color: _selectedSlot == slot
                              ? _slotColor(slot)
                              : colors.outlineVariant,
                        ),
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
              // Date Filter & clear
              Row(
                children: [
                  ActionChip(
                    avatar: Icon(
                      Icons.calendar_month_outlined,
                      size: 16,
                      color: _selectedDate != null
                          ? colors.primary
                          : const Color(0xFF64748B),
                    ),
                    label: Text(
                      _selectedDate == null
                          ? 'Lọc theo ngày: Tất cả'
                          : 'Ngày: $_selectedDate',
                      style: TextStyle(
                        fontWeight: _selectedDate != null
                            ? FontWeight.w600
                            : FontWeight.normal,
                        color: _selectedDate != null ? colors.primary : null,
                      ),
                    ),
                    onPressed: _pickDate,
                  ),
                  if (_selectedDate != null) ...[
                    const SizedBox(width: 8),
                    TextButton.icon(
                      onPressed: () {
                        setState(() => _selectedDate = null);
                        _loadEvents();
                      },
                      icon: const Icon(Icons.close_rounded, size: 16),
                      label: const Text('Xóa ngày'),
                      style: TextButton.styleFrom(
                        visualDensity: VisualDensity.compact,
                      ),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),

        // Timeline List
        Expanded(
          child: _loading && filtered.isEmpty
              ? const Center(child: CircularProgressIndicator())
              : _error != null
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.error_outline_rounded,
                                size: 48, color: colors.error),
                            const SizedBox(height: 12),
                            Text(
                              _error!,
                              textAlign: TextAlign.center,
                              style: TextStyle(color: colors.error),
                            ),
                            const SizedBox(height: 16),
                            FilledButton.icon(
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
                            padding: const EdgeInsets.all(32),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(20),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFF1F5F9),
                                    shape: BoxShape.circle,
                                  ),
                                  child: const Icon(
                                    Icons.history_toggle_off_rounded,
                                    size: 48,
                                    color: Color(0xFF94A3B8),
                                  ),
                                ),
                                const SizedBox(height: 16),
                                Text(
                                  'Chưa có sự kiện nào phù hợp với bộ lọc.',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    fontSize: 15,
                                    fontWeight: FontWeight.w500,
                                    color: colors.onSurfaceVariant,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  'Các thao tác mở nắp, lấy thuốc và bấm xác nhận trên hộp sẽ xuất hiện tại đây theo thời gian thực.',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    fontSize: 13,
                                    color: const Color(0xFF94A3B8),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: _loadEvents,
                          child: ListView.builder(
                            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
                            itemCount: filtered.length,
                            itemBuilder: (context, index) {
                              final event = filtered[index];
                              final isFirst = index == 0;
                              final isLast = index == filtered.length - 1;
                              final evColor = _eventColor(event.eventType);
                              final slotColor = _slotColor(event.slot);
                              final slotLabel = event.slot != null
                                  ? 'Ngăn ${event.slot}'
                                  : 'Hệ thống';
                              final formattedTime =
                                  _formatTimestamp(event.timestamp);

                              // Payload indicators
                              final payload = event.payload;
                              final weight = payload['weight_grams'] ??
                                  payload['new_weight'];
                              final delta = payload['delta_grams'];
                              final minutes = payload['minutes'];

                              return IntrinsicHeight(
                                child: Row(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.stretch,
                                  children: [
                                    // Timeline Rail
                                    SizedBox(
                                      width: 44,
                                      child: Stack(
                                        alignment: Alignment.center,
                                        children: [
                                          // Vertical connector
                                          Positioned(
                                            top: isFirst ? 20 : 0,
                                            bottom: isLast ? 20 : 0,
                                            child: Container(
                                              width: 2,
                                              color: const Color(0xFFE2E8F0),
                                            ),
                                          ),
                                          // Node dot
                                          Container(
                                            width: 32,
                                            height: 32,
                                            decoration: BoxDecoration(
                                              color: Colors.white,
                                              shape: BoxShape.circle,
                                              border: Border.all(
                                                color: evColor,
                                                width: 2.5,
                                              ),
                                              boxShadow: [
                                                BoxShadow(
                                                  color: evColor.withValues(alpha: 0.2),
                                                  blurRadius: 6,
                                                  offset: const Offset(0, 2),
                                                ),
                                              ],
                                            ),
                                            child: Center(
                                              child: Icon(
                                                _eventIcon(event.eventType),
                                                size: 16,
                                                color: evColor,
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(width: 8),

                                    // Event Content Card
                                    Expanded(
                                      child: Container(
                                        margin:
                                            const EdgeInsets.only(bottom: 12),
                                        decoration: BoxDecoration(
                                          color: Colors.white,
                                          borderRadius:
                                              BorderRadius.circular(14),
                                          border: Border.all(
                                            color:
                                                const Color(0xFFE2E8F0),
                                          ),
                                          boxShadow: [
                                            BoxShadow(
                                              color: Colors.black
                                                  .withValues(alpha: 0.02),
                                              blurRadius: 4,
                                              offset: const Offset(0, 1),
                                            ),
                                          ],
                                        ),
                                        child: Padding(
                                          padding: const EdgeInsets.all(12),
                                          child: Column(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.start,
                                            children: [
                                              // Top row: Title + Slot badge & Time
                                              Row(
                                                mainAxisAlignment:
                                                    MainAxisAlignment
                                                        .spaceBetween,
                                                children: [
                                                  Expanded(
                                                    child: Text(
                                                      _eventTitle(
                                                          event.eventType),
                                                      style: const TextStyle(
                                                        fontWeight:
                                                            FontWeight.w700,
                                                        fontSize: 14,
                                                        color:
                                                            Color(0xFF0F172A),
                                                      ),
                                                    ),
                                                  ),
                                                  Row(
                                                    mainAxisSize:
                                                        MainAxisSize.min,
                                                    children: [
                                                      Text(
                                                        formattedTime,
                                                        style: const TextStyle(
                                                          fontSize: 11,
                                                          fontWeight:
                                                              FontWeight.w600,
                                                          color:
                                                              Color(0xFF64748B),
                                                        ),
                                                      ),
                                                      const SizedBox(width: 6),
                                                      Container(
                                                        padding:
                                                            const EdgeInsets
                                                                .symmetric(
                                                          horizontal: 8,
                                                          vertical: 2,
                                                        ),
                                                        decoration:
                                                            BoxDecoration(
                                                          color: slotColor
                                                              .withValues(
                                                                  alpha: 0.12),
                                                          borderRadius:
                                                              BorderRadius
                                                                  .circular(6),
                                                        ),
                                                        child: Text(
                                                          slotLabel,
                                                          style: TextStyle(
                                                            fontSize: 11,
                                                            fontWeight:
                                                                FontWeight.bold,
                                                            color: slotColor,
                                                          ),
                                                        ),
                                                      ),
                                                    ],
                                                  ),
                                                ],
                                              ),
                                              const SizedBox(height: 6),

                                              // Subtitle: Date & Time
                                              Text(
                                                '$slotLabel · Ngày: ${event.dateKey}\nThời gian: ${event.timestamp}',
                                                style: TextStyle(
                                                  fontSize: 12,
                                                  color: const Color(0xFF64748B),
                                                  height: 1.35,
                                                ),
                                              ),

                                              // Extra metrics if available
                                              if (weight != null ||
                                                  delta != null ||
                                                  minutes != null) ...[
                                                const SizedBox(height: 8),
                                                Wrap(
                                                  spacing: 6,
                                                  children: [
                                                    if (weight != null)
                                                      Container(
                                                        padding:
                                                            const EdgeInsets
                                                                .symmetric(
                                                          horizontal: 6,
                                                          vertical: 2,
                                                        ),
                                                        decoration:
                                                            BoxDecoration(
                                                          color: const Color(
                                                              0xFFF1F5F9),
                                                          borderRadius:
                                                              BorderRadius
                                                                  .circular(4),
                                                        ),
                                                        child: Row(
                                                          mainAxisSize:
                                                              MainAxisSize.min,
                                                          children: [
                                                            const Icon(
                                                              Icons
                                                                  .scale_rounded,
                                                              size: 12,
                                                              color: Color(
                                                                  0xFF475569),
                                                            ),
                                                            const SizedBox(
                                                                width: 4),
                                                            Text(
                                                              'Cân: ${weight}g',
                                                              style:
                                                                  const TextStyle(
                                                                fontSize: 11,
                                                                fontWeight:
                                                                    FontWeight
                                                                        .w600,
                                                                color: Color(
                                                                    0xFF334155),
                                                              ),
                                                            ),
                                                          ],
                                                        ),
                                                      ),
                                                    if (delta != null)
                                                      Container(
                                                        padding:
                                                            const EdgeInsets
                                                                .symmetric(
                                                          horizontal: 6,
                                                          vertical: 2,
                                                        ),
                                                        decoration:
                                                            BoxDecoration(
                                                          color: const Color(
                                                              0xFFEFF6FF),
                                                          borderRadius:
                                                              BorderRadius
                                                                  .circular(4),
                                                        ),
                                                        child: Text(
                                                          'Δ: ${delta}g',
                                                          style:
                                                              const TextStyle(
                                                            fontSize: 11,
                                                            fontWeight:
                                                                FontWeight.w600,
                                                            color: Color(
                                                                0xFF1D4ED8),
                                                          ),
                                                        ),
                                                      ),
                                                    if (minutes != null)
                                                      Container(
                                                        padding:
                                                            const EdgeInsets
                                                                .symmetric(
                                                          horizontal: 6,
                                                          vertical: 2,
                                                        ),
                                                        decoration:
                                                            BoxDecoration(
                                                          color: const Color(
                                                              0xFFF0FDF4),
                                                          borderRadius:
                                                              BorderRadius
                                                                  .circular(4),
                                                        ),
                                                        child: Text(
                                                          '+$minutes phút',
                                                          style:
                                                              const TextStyle(
                                                            fontSize: 11,
                                                            fontWeight:
                                                                FontWeight.w600,
                                                            color: Color(
                                                                0xFF15803D),
                                                          ),
                                                        ),
                                                      ),
                                                  ],
                                                ),
                                              ],
                                            ],
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
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
