"""CleanSweep 图形界面（PySide6，仅 Linux）。

勾选要清理的项 → 点「开始清理」→ 逐项执行；涉及 sudo 的项用 pkexec，由系统
polkit 弹密码框。清理在后台线程跑，输出实时回显到下方日志区。

入口与 CLI 的 main.py 平级：`uv run gui.py`。
"""

import sys

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cleaners.executor import has_pkexec, run_task
from cleaners.registry import CATEGORY_TITLES, TASKS, Task


class CleanWorker(QThread):
    """在后台线程里按顺序执行选中的任务。"""

    line = Signal(str)  # 一行日志
    task_started = Signal(str)  # 开始某个任务（label）
    done = Signal()

    def __init__(self, tasks: list[Task]) -> None:
        super().__init__()
        self._tasks = tasks

    def run(self) -> None:
        for task in self._tasks:
            self.task_started.emit(task.label)
            try:
                run_task(task, self.line.emit)
            except Exception as e:  # noqa: BLE001 - 单项失败不应中断整体
                self.line.emit(f"[{task.label}] 执行异常: {e}")
        self.done.emit()


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CleanSweep")
        self.resize(820, 720)
        self._checks: dict[str, QCheckBox] = {}
        self._worker: CleanWorker | None = None
        self._build_ui()

    # ---- 构建界面 ----
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        title = QLabel("CleanSweep — 选择要清理的项目")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        root.addWidget(title)

        hint = QLabel(
            "勾选后点下方按钮开始。标「管理员」的项需要管理员权限，会弹系统密码框；"
            "标「敏感」的项删的是用户数据 / 配置 / 系统状态，请确认后再勾选。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        root.addWidget(hint)

        # 全选 / 全不选
        bar = QHBoxLayout()
        select_all = QPushButton("全选可用项")
        select_all.clicked.connect(lambda: self._set_all(True))
        select_none = QPushButton("全不选")
        select_none.clicked.connect(lambda: self._set_all(False))
        bar.addWidget(select_all)
        bar.addWidget(select_none)
        bar.addStretch()
        root.addLayout(bar)

        # 可滚动的勾选区，按分类分组
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        self._list_layout = QVBoxLayout(inner)
        self._populate_tasks()
        self._list_layout.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll, stretch=3)

        # 开始清理按钮
        self._clean_btn = QPushButton("开始清理")
        self._clean_btn.setStyleSheet("font-size: 14px; padding: 8px;")
        self._clean_btn.clicked.connect(self._on_clean)
        root.addWidget(self._clean_btn)

        # 日志区
        root.addWidget(QLabel("执行日志："))
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet("font-family: monospace;")
        root.addWidget(self._log, stretch=2)

    @staticmethod
    def _make_badge(text: str, color: str) -> QLabel:
        """一个带背景色的小标签，用来替代不一定有字体的 emoji。"""
        badge = QLabel(text)
        badge.setStyleSheet(
            f"background: {color}; color: white; border-radius: 4px;"
            "padding: 1px 6px; font-size: 11px; font-weight: bold;"
        )
        return badge

    def _populate_tasks(self) -> None:
        last_category: str | None = None
        for task in TASKS:
            if task.category != last_category:
                last_category = task.category
                header = QLabel(CATEGORY_TITLES.get(task.category, task.category))
                header.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 10px;")
                self._list_layout.addWidget(header)
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                self._list_layout.addWidget(line)

            available = task.detect()

            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(4, 1, 4, 1)
            h.setSpacing(6)

            cb = QCheckBox(task.label)
            h.addWidget(cb)
            if task.privileged:
                h.addWidget(self._make_badge("管理员", "#d98c00"))
            if task.sensitive:
                h.addWidget(self._make_badge("敏感", "#c0392b"))

            detail_text = f"— {task.detail}"
            if not available:
                detail_text += "（未检测到，跳过）"
            detail = QLabel(detail_text)
            detail.setStyleSheet("color: gray;")
            h.addWidget(detail)
            h.addStretch()

            tip = task.detail
            if available:
                extra = task.note()
                if extra:
                    tip = f"{task.detail}\n目标：{extra}"
            else:
                cb.setEnabled(False)
            cb.setToolTip(tip)
            row.setToolTip(tip)

            self._checks[task.key] = cb
            self._list_layout.addWidget(row)

    # ---- 交互 ----
    def _set_all(self, checked: bool) -> None:
        for cb in self._checks.values():
            if cb.isEnabled():
                cb.setChecked(checked)

    def _selected_tasks(self) -> list[Task]:
        return [
            t for t in TASKS
            if self._checks[t.key].isEnabled() and self._checks[t.key].isChecked()
        ]

    def _on_clean(self) -> None:
        tasks = self._selected_tasks()
        if not tasks:
            QMessageBox.information(self, "未选择", "请先勾选至少一项再清理。")
            return

        if any(t.privileged for t in tasks) and not has_pkexec():
            QMessageBox.warning(
                self,
                "缺少 pkexec",
                "选中项里有需要管理员权限的清理，但系统未安装 pkexec，"
                "无法弹出密码框。请取消这些项或安装 polkit（pkexec）。",
            )
            return

        # 销毁性操作，执行前再确认一次，列出选中项
        names = "\n".join(f"  • {t.label}" for t in tasks)
        sensitive = [t for t in tasks if t.sensitive]
        warn = ""
        if sensitive:
            warn = (
                "\n\n其中以下项删除的是用户数据 / 配置 / 系统状态，无法撤销：\n"
                + "\n".join(f"  [敏感] {t.label}" for t in sensitive)
            )
        reply = QMessageBox.question(
            self,
            "确认清理",
            f"将依次清理以下 {len(tasks)} 项：\n{names}{warn}\n\n确定继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._start_worker(tasks)

    def _start_worker(self, tasks: list[Task]) -> None:
        self._set_ui_running(True)
        self._log.clear()
        self._worker = CleanWorker(tasks)
        self._worker.task_started.connect(
            lambda name: self._append(f"\n=== {name} ===")
        )
        self._worker.line.connect(self._append)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _append(self, text: str) -> None:
        self._log.appendPlainText(text)

    def _on_done(self) -> None:
        self._append("\n=== 全部完成 ===")
        self._set_ui_running(False)
        self._worker = None
        QMessageBox.information(self, "完成", "清理结束。")

    def _set_ui_running(self, running: bool) -> None:
        self._clean_btn.setEnabled(not running)
        self._clean_btn.setText("清理中…" if running else "开始清理")
        for cb in self._checks.values():
            cb.setEnabled(False if running else cb.property("orig_enabled"))

    def showEvent(self, event) -> None:  # noqa: N802 - Qt 命名
        # 记录每个 checkbox 原始的可用状态，便于运行结束后恢复
        for cb in self._checks.values():
            if cb.property("orig_enabled") is None:
                cb.setProperty("orig_enabled", cb.isEnabled())
        super().showEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


main()
