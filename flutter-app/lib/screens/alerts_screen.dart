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
                            padding: const EdgeInsets.all(24),
                            child: Text(
                              'Hiện không có cảnh báo nào.',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: colors.onSurfaceVariant),
                            ),
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: _loadAlerts,
                          child: ListView.builder(
                            padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
                            itemCount: _alerts.length,
                            itemBuilder: (context, index) {
                              final alert = _alerts[index];
                              final statusColor =
                                  _statusColor(context, alert.status);
                              final noteLine = (alert.note != null &&
                                      alert.note!.trim().isNotEmpty)
                                  ? '\nGhi chú: ${alert.note}'
                                  : '';
                              return Card(
                                margin: const EdgeInsets.only(bottom: 10),
                                child: ListTile(
                                  leading: CircleAvatar(
                                    backgroundColor:
                                        statusColor.withValues(alpha: 0.14),
                                    child: Icon(
                                      alert.isPending
                                          ? Icons.warning_amber_rounded
                                          : Icons.task_alt,
                                      color: statusColor,
                                    ),
                                  ),
                                  title: Text(
                                    alert.message,
                                    style: TextStyle(
                                      fontWeight: alert.isPending
                                          ? FontWeight.w700
                                          : FontWeight.w500,
                                    ),
                                  ),
                                  subtitle: Text(
                                    'Trạng thái: ${statusLabel(alert.status)} · ${alert.createdAt}$noteLine',
                                  ),
                                  isThreeLine: true,
                                  trailing: alert.isPending
                                      ? const Icon(Icons.chevron_right)
                                      : null,
                                  onTap: () => _showResolveDialog(alert),
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
      AlertItem updated;
      if (widget.api != null && widget.api!.token != null) {
        updated = await widget.api!.updateAlert(
          widget.alert.id,
          status: _selectedStatus,
          note: note,
        );
      } else {
        updated = AlertItem(
          id: widget.alert.id,
          patientId: widget.alert.patientId,
          occurrenceId: widget.alert.occurrenceId,
          kind: widget.alert.kind,
          status: _selectedStatus,
          message: widget.alert.message,
          note: note.isEmpty ? widget.alert.note : note,
          createdAt: widget.alert.createdAt,
          resolvedAt: DateTime.now().toIso8601String(),
        );
      }
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
    return AlertDialog(
      title: const Text('Xử lý cảnh báo'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              widget.alert.message,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 16),
            const Text(
              'Chọn thao tác xử lý:',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
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
                style: TextStyle(
                  color: Theme.of(context).colorScheme.error,
                  fontSize: 13,
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
          onPressed: _busy ? null : _submit,
          child: Text(_busy ? 'Đang lưu…' : 'Xác nhận'),
        ),
      ],
    );
  }
}
