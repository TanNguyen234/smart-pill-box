import 'package:flutter/material.dart';

import '../api/smart_pill_api.dart';
import '../models.dart';

class AlertsScreen extends StatefulWidget {
  const AlertsScreen({
    super.key,
    this.api,
    this.initialAlerts,
  });

  final SmartPillApi? api;
  final List<AlertItem>? initialAlerts;

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  List<AlertItem> _alerts = [];
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (widget.initialAlerts != null) {
      _alerts = widget.initialAlerts!;
    } else if (widget.api?.token != null) {
      _loadAlerts();
    }
  }

  Future<void> refreshAlerts() => _loadAlerts();

  Future<void> _loadAlerts() async {
    final api = widget.api;
    if (api == null || api.token == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await api.alerts();
      if (!mounted) return;
      setState(() {
        _alerts = items;
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

  static String statusLabel(String status) {
    switch (status.toUpperCase()) {
      case 'CHECKED':
        return 'Đã kiểm tra';
      case 'ASSISTED':
        return 'Đã hỗ trợ';
      case 'IGNORED':
        return 'Bỏ qua';
      default:
        return 'Chờ xử lý';
    }
  }

  Color _statusColor(BuildContext context, String status) {
    switch (status.toUpperCase()) {
      case 'CHECKED':
        return Colors.blue.shade700;
      case 'ASSISTED':
        return Colors.green.shade700;
      case 'IGNORED':
        return Colors.grey.shade700;
      default:
        return Theme.of(context).colorScheme.error;
    }
  }

  Future<void> _showResolveDialog(AlertItem alert) async {
    final updated = await showDialog<AlertItem>(
      context: context,
      builder: (_) => _ResolveAlertDialog(
        alert: alert,
        api: widget.api,
      ),
    );
    if (updated != null && mounted) {
      setState(() {
        _alerts = _alerts
            .map((item) => item.id == updated.id ? updated : item)
            .toList();
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Đã cập nhật cảnh báo: ${statusLabel(updated.status)}'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Danh sách cảnh báo',
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(fontWeight: FontWeight.w600),
              ),
              IconButton(
                onPressed: _loading ? null : _loadAlerts,
                tooltip: 'Làm mới cảnh báo',
                icon: const Icon(Icons.refresh),
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
                              onPressed: _loadAlerts,
                              icon: const Icon(Icons.refresh),
                              label: const Text('Thử lại'),
                            ),
                          ],
                        ),
                      ),
                    )
                  : _alerts.isEmpty
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(32),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Container(
                                  width: 72,
                                  height: 72,
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFCCFBF1),
                                    borderRadius: BorderRadius.circular(24),
                                  ),
                                  child: const Icon(Icons.shield_outlined, size: 36, color: Color(0xFF0F766E)),
                                ),
                                const SizedBox(height: 18),
                                const Text(
                                  'Hiện không có cảnh báo nào.',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
                                ),
                                const SizedBox(height: 6),
                                const Text(
                                  'Người thân đang uống thuốc đúng giờ hoặc chưa đến giờ nhắc.',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(color: Color(0xFF64748B), fontSize: 13),
                                ),
                              ],
                            ),
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: _loadAlerts,
                          child: ListView.builder(
                            padding: const EdgeInsets.fromLTRB(20, 6, 20, 32),
                            itemCount: _alerts.length,
                            itemBuilder: (context, index) {
                              final alert = _alerts[index];
                              final statusColor = _statusColor(context, alert.status);
                              final noteLine = (alert.note != null && alert.note!.trim().isNotEmpty)
                                  ? '\nGhi chú: ${alert.note}'
                                  : '';
                              return Card(
                                margin: const EdgeInsets.only(bottom: 12),
                                child: Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: Row(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Container(
                                        width: 44,
                                        height: 44,
                                        decoration: BoxDecoration(
                                          color: statusColor.withValues(alpha: 0.12),
                                          borderRadius: BorderRadius.circular(14),
                                        ),
                                        alignment: Alignment.center,
                                        child: Icon(
                                          alert.isPending ? Icons.warning_amber_rounded : Icons.check_circle_outline,
                                          color: statusColor,
                                          size: 24,
                                        ),
                                      ),
                                      const SizedBox(width: 14),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              alert.message,
                                              style: TextStyle(
                                                fontWeight: alert.isPending ? FontWeight.w800 : FontWeight.w600,
                                                fontSize: 15,
                                                color: const Color(0xFF0F172A),
                                              ),
                                            ),
                                            const SizedBox(height: 6),
                                            Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                              decoration: BoxDecoration(
                                                color: statusColor.withValues(alpha: 0.1),
                                                borderRadius: BorderRadius.circular(6),
                                              ),
                                              child: Text(
                                                'Trạng thái: ${statusLabel(alert.status)}',
                                                style: TextStyle(color: statusColor, fontWeight: FontWeight.w700, fontSize: 11),
                                              ),
                                            ),
                                            if (noteLine.isNotEmpty) ...[
                                              const SizedBox(height: 4),
                                              Text(
                                                noteLine.trim(),
                                                style: const TextStyle(color: Color(0xFF64748B), fontSize: 12, fontStyle: FontStyle.italic),
                                              ),
                                            ],
                                            const SizedBox(height: 6),
                                            Text(
                                              alert.createdAt,
                                              style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                                            ),
                                          ],
                                        ),
                                      ),
                                      if (alert.isPending)
                                        FilledButton(
                                          style: FilledButton.styleFrom(
                                            backgroundColor: const Color(0xFF0F766E),
                                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                            minimumSize: const Size(0, 36),
                                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                          ),
                                          onPressed: () => _showResolveDialog(alert),
                                          child: const Text('Xử lý', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                                        ),
                                    ],
                                  ),
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

class _ResolveAlertDialog extends StatefulWidget {
  const _ResolveAlertDialog({
    required this.alert,
    this.api,
  });

  final AlertItem alert;
  final SmartPillApi? api;

  @override
  State<_ResolveAlertDialog> createState() => _ResolveAlertDialogState();
}

class _ResolveAlertDialogState extends State<_ResolveAlertDialog> {
  late final TextEditingController _noteController;
  String _selectedStatus = 'CHECKED';
  String? _error;
  bool _busy = false;

  final Map<String, List<String>> _presets = {
    'CHECKED': ['Đã kiểm tra khay thuốc', 'Người nhà đã mở nắp', 'Đã hỏi thăm qua điện thoại'],
    'ASSISTED': ['Đã gọi điện nhắc uống thuốc', 'Đã cho uống thuốc trực tiếp', 'Nhờ người nhà hỗ trợ'],
    'IGNORED': ['Đã uống nhưng quên bấm nút', 'Bác đi vắng chưa về', 'Bác bị ốm/bỏ cữ thuốc'],
  };

  @override
  void initState() {
    super.initState();
    _noteController = TextEditingController(text: widget.alert.note ?? '');
  }

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final note = _noteController.text.trim();
    if (_selectedStatus == 'IGNORED' && note.isEmpty) {
      setState(() {
        _error = 'Vui lòng nhập lý do khi chọn Bỏ qua cảnh báo.';
      });
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final api = widget.api;
      if (api == null || api.token == null) {
        throw const ApiException('Chưa đăng nhập hoặc không có kết nối API.');
      }
      final updated = await api.updateAlert(
        widget.alert.id,
        status: _selectedStatus,
        note: note,
      );
      if (mounted) {
        Navigator.pop(context, updated);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _busy = false;
          _error = e.toString();
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final currentPresets = _presets[_selectedStatus] ?? [];
    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      title: const Text('Xử lý cảnh báo', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF2F2),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFFECACA)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.warning_amber_rounded, color: Color(0xFFDC2626), size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      widget.alert.message,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: Color(0xFF991B1B)),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            const Text(
              'Chọn phương án xử lý:',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: Color(0xFF334155)),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ChoiceChip(
                  label: const Text('Đã kiểm tra'),
                  selected: _selectedStatus == 'CHECKED',
                  onSelected: (selected) {
                    if (selected) {
                      setState(() {
                        _selectedStatus = 'CHECKED';
                        _error = null;
                      });
                    }
                  },
                ),
                ChoiceChip(
                  label: const Text('Đã hỗ trợ'),
                  selected: _selectedStatus == 'ASSISTED',
                  onSelected: (selected) {
                    if (selected) {
                      setState(() {
                        _selectedStatus = 'ASSISTED';
                        _error = null;
                      });
                    }
                  },
                ),
                ChoiceChip(
                  label: const Text('Bỏ qua'),
                  selected: _selectedStatus == 'IGNORED',
                  onSelected: (selected) {
                    if (selected) {
                      setState(() {
                        _selectedStatus = 'IGNORED';
                        _error = null;
                      });
                    }
                  },
                ),
              ],
            ),
            if (currentPresets.isNotEmpty) ...[
              const SizedBox(height: 14),
              const Text('Gợi ý ghi chú nhanh:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Color(0xFF64748B))),
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: currentPresets.map((preset) {
                  return ActionChip(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    label: Text(preset, style: const TextStyle(fontSize: 11)),
                    onPressed: () {
                      _noteController.text = preset;
                    },
                  );
                }).toList(),
              ),
            ],
            const SizedBox(height: 14),
            TextField(
              controller: _noteController,
              maxLines: 2,
              decoration: InputDecoration(
                labelText: _selectedStatus == 'IGNORED'
                    ? 'Lý do bỏ qua (bắt buộc)'
                    : 'Ghi chú xử lý (tùy chọn)',
                hintText: _selectedStatus == 'IGNORED'
                    ? 'Nhập lý do bỏ qua cảnh báo...'
                    : 'Nhập ghi chú kiểm tra / hỗ trợ...',
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 10),
              Text(
                _error!,
                style: const TextStyle(
                  color: Color(0xFFDC2626),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _busy ? null : () => Navigator.pop(context),
          child: const Text('Hủy'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: const Color(0xFF0F766E)),
          onPressed: _busy ? null : _submit,
          child: Text(_busy ? 'Đang lưu…' : 'Xác nhận'),
        ),
      ],
    );
  }
}
