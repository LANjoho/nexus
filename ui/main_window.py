import customtkinter as ctk
from tkinter import messagebox
from controllers.room_controller import RoomController
from database.db import Database
from models.enums import RoomStatus, UpdateSource
from controllers.metrics_controller import MetricsController
from datetime import datetime, timedelta
from services.shift_service import ShiftService

# ----------------------------
# Initialize DB and controller
# ----------------------------
db = Database()
controller = RoomController(db)

# ----------------------------
# Status priority mapping
# ----------------------------

STATUS_PRIORITY = {
    RoomStatus.NEEDS_CLEANING: 0,
    RoomStatus.CLEANING: 1,
    #RoomStatus.OCCUPIED: 2,
    RoomStatus.WAITING: 2,
    RoomStatus.SEEING_PROVIDER: 3,
    RoomStatus.AVAILABLE: 4,
    RoomStatus.MAINTENANCE: 5,
    RoomStatus.OUT_OF_SERVICE: 6,
}

# ----------------------------
# Color mapping for statuses
# ----------------------------

STATUS_COLORS = {
    RoomStatus.AVAILABLE: "#4CAF50",       # Green
    RoomStatus.WAITING: "#FFEB3B",         # Yellow
    RoomStatus.SEEING_PROVIDER: "#FF0000", # Purple
    #RoomStatus.OCCUPIED: "#F44336",        # Red
    RoomStatus.NEEDS_CLEANING: "#FF9800",  # Orange
    RoomStatus.CLEANING: "#2196F3",        # Blue
    RoomStatus.MAINTENANCE: "#444444",     # Gray
    RoomStatus.OUT_OF_SERVICE: "#FFFFFF",   # White
}

# ----------------------------
# Room Tile Widget
# ----------------------------
class RoomTile(ctk.CTkFrame):
    def __init__(self, master, room, controller):
        super().__init__(master, corner_radius=10, border_width=1, border_color="black")
        self.room = room
        self.controller = controller
        self.grid_propagate(True)

        # Room Name
        self.name_label = ctk.CTkLabel(self, text=room["name"], font=("Arial", 14, "bold"))
        self.name_label.grid(row=0, column=0, columnspan=3, pady=(5, 0))

        # Status Label
        self.status_label = ctk.CTkLabel(
            self,
            text=room["status"],
            fg_color=STATUS_COLORS.get(RoomStatus(room["status"]), "#FFFFFF"),
            corner_radius=5,
        )
        self.status_label.grid(row=1, column=0, columnspan=3, pady=5, sticky="ew")

        # Buttons — single loop only
        max_cols = 3  # number of buttons per row
        self.buttons = []
        for idx, status in enumerate(RoomStatus):
            row = 2 + (idx // max_cols)
            col = idx % max_cols
            btn = ctk.CTkButton(
                self,
                text=status.value,
                width=60,
                height=25,
                fg_color=STATUS_COLORS.get(status, "#CCCCCC"),
                command=lambda s=status: self.update_status(s),
            )
            btn.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
            self.buttons.append(btn)

    def update_status(self, new_status):
        current_status = RoomStatus(self.room["status"])
        
        # Optional: skip no-op updates
        if new_status == current_status:
            return
        
        confirmed = messagebox.askyesno(
            "Confirm Status Change",
            f"Are you sure you want to change status of {self.room['name']} from {current_status.value} to {new_status.value}?"
        )
        if not confirmed:
            return
        
        self.controller.update_status(self.room["id"], new_status, UpdateSource.MANUAL)
        self.refresh()



    def refresh(self):
        room_dict = {r["id"]: r for r in self.controller.get_all_rooms()}
        if self.room["id"] not in room_dict:
            self.destroy()
            return        
        self.room = room_dict[self.room["id"]]
        self.status_label.configure(
            text=self.room["status"],
            fg_color=STATUS_COLORS.get(RoomStatus(self.room["status"]), "#CCCCCC"),
        )
class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Clinical Room Manager")
        
        self.geometry("1000x700")

        self.shift_service = ShiftService()
        self.db = None
        self.controller = None
        self.metrics_controller = None
        
        self.active_start_date = None
        self.active_end_date = None
        
        # Tabs
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.rooms_tab = self.tabs.add("Rooms")
        self.metrics_tab = self.tabs.add("Metrics")
        
        # Scrollable Frame
        
        self.metric_labels = {}
        self.room_tiles = []

        self._build_rooms_tab()
        self._build_metrics_tab()

        self.initialize_active_shift()
        self.auto_refresh()

    def _build_rooms_tab(self):
        controls = ctk.CTkFrame(self.rooms_tab)
        controls.pack(fill="x", padx=10, pady=(10, 6))

        self.shift_status_label = ctk.CTkLabel(controls, text="Shift: none")
        self.shift_status_label.pack(side="left", padx=(8, 16), pady=8)

        ctk.CTkButton(controls, text="Start Shift", command=self.start_shift).pack(side="left", padx=4)
        ctk.CTkButton(controls, text="End Shift", command=self.end_shift).pack(side="left", padx=4)
        ctk.CTkButton(controls, text="Add Room", command=self.add_room_dialog).pack(side="left", padx=20)
        ctk.CTkButton(controls, text="Remove Room", command=self.remove_room_dialog).pack(side="left", padx=4)
        
        self.scrollable_frame = ctk.CTkScrollableFrame(self.rooms_tab)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def _build_metrics_tab(self):
        metrics_frame = ctk.CTkFrame(self.metrics_tab)
        metrics_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ----------------------------
        # Custom Date Range Selector
        # ----------------------------
        
        self.build_date_vars()

        date_frame = ctk.CTkFrame(metrics_frame)
        date_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))

        years = list(range(2020, datetime.now().year + 1))
        months = list(range(1, 13))
        days = list(range(1, 32))

        def date_dropdown(parent, var, values):
            return ctk.CTkOptionMenu(parent, values=[str(v).zfill(2) for v in values], variable=var)

        # --- Start Date ---
        ctk.CTkLabel(date_frame, text="Start Date").grid(row=0, column=0, padx=5)

        date_dropdown(date_frame, self.start_year, years).grid(row=0, column=1)
        date_dropdown(date_frame, self.start_month, months).grid(row=0, column=2)
        date_dropdown(date_frame, self.start_day, days).grid(row=0, column=3)

        # --- End Date ---
        ctk.CTkLabel(date_frame, text="End Date").grid(row=1, column=0, padx=5)

        date_dropdown(date_frame, self.end_year, years).grid(row=1, column=1)
        date_dropdown(date_frame, self.end_month, months).grid(row=1, column=2)
        date_dropdown(date_frame, self.end_day, days).grid(row=1, column=3)

        ctk.CTkButton(date_frame, text="Apply", command=self.apply_date_filter).grid(row=0, column=4, rowspan=2, padx=15)
        #--- Metric Labels ---
        
        def add_metric(key, label, row):
            title = ctk.CTkLabel(metrics_frame, text=label, font=("Arial", 16, "bold"))
            title.grid(row=row + 1, column=0, sticky="w", pady=10)

            value = ctk.CTkLabel(metrics_frame, text="-", font=("Arial", 16))
            value.grid(row=row + 1, column=1, sticky="w", pady=10)

            self.metric_labels[key] = value

        add_metric("avg_wait", "Average Waiting Time:", 0)
        add_metric("avg_provider", "Average Seeing Provider Time:", 1)
        add_metric("avg_cleaning", "Average Cleaning Time:", 2)
        add_metric("turnovers", "Total Turnovers:", 3)
        add_metric("stuck_rooms", "Rooms Stuck Needing Cleaning:", 4)
        
    def initialize_active_shift(self):
        active = self.shift_service.get_active_db_path()
        if active:
            self._bind_database(active)
            self.shift_status_label.configure(text=f"Shift: ACTIVE ({active.name})")
        else:
            self.shift_status_label.configure(text="Shift: none (click Start Shift)")

    def _bind_database(self, db_path):
        if self.db:
            self.db.close()

        self.db = Database(str(db_path))
        self.controller = RoomController(self.db)
        self.metrics_controller = MetricsController(self.db)
        self.reload_rooms()
        self.refresh_metrics()

    def start_shift(self):
        db_path, created = self.shift_service.start_shift()
        self._bind_database(db_path)

        if created:
            messagebox.showinfo("Shift Started", f"Shift database created:\n{db_path}")
        else:
            messagebox.showinfo("Shift Already Active", f"Using active shift database:\n{db_path}")

        self.shift_status_label.configure(text=f"Shift: ACTIVE ({db_path.name})")

    def end_shift(self):
        if not self.db:
            messagebox.showwarning("No Active Shift", "There is no active shift to end.")
            return

        confirmed = messagebox.askyesno("Confirm End Shift", "End current shift and archive its database?")
        if not confirmed:
            return

        self.db.close()
        self.db = None
        self.controller = None
        self.metrics_controller = None

        old_path, archived_path, ended = self.shift_service.end_shift()
        if not ended:
            messagebox.showwarning("No Active Shift", "There is no active shift to end.")
            return

        self.shift_status_label.configure(text="Shift: none (click Start Shift)")
        self.clear_rooms()

        messagebox.showinfo(
            "Shift Ended",
            f"Archived shift database:\n{archived_path}\n\n"
            "Next step: upload this archived DB to your long-term analytics store.",
        )

    def add_room_dialog(self):
        if not self.controller:
            messagebox.showwarning("No Active Shift", "Start a shift before adding rooms.")
            return

        dialog = ctk.CTkInputDialog(text="Enter new room name:", title="Add Room")
        room_name = dialog.get_input()
        if not room_name:
            return

        room_name = room_name.strip()
        if not room_name:
            return

        try:
            self.controller.create_room(room_name, initial_status=RoomStatus.AVAILABLE)
        except Exception as exc:
            messagebox.showerror("Add Room Failed", str(exc))
            return

        self.reload_rooms()

    def remove_room_dialog(self):
        if not self.controller:
            messagebox.showwarning("No Active Shift", "Start a shift before removing rooms.")
            return

        dialog = ctk.CTkInputDialog(text="Enter room name to remove:", title="Remove Room")
        room_name = dialog.get_input()
        if not room_name:
            return

        room_name = room_name.strip()
        rooms = self.controller.get_all_rooms()
        match = next((r for r in rooms if r["name"].lower() == room_name.lower()), None)

        if not match:
            messagebox.showwarning("Room Not Found", f"No room named '{room_name}' was found.")
            return

        confirmed = messagebox.askyesno(
            "Confirm Room Removal",
            f"Remove room '{match['name']}' and all of its visit/event history?",
        )
        if not confirmed:
            return

        self.controller.delete_room(match["id"])
        self.reload_rooms()

    def apply_date_filter(self):
        self.apply_date_range()
        self.refresh_metrics()

        
    def build_date_vars(self):
        now = datetime.now()
        
        self.start_year = ctk.IntVar(value=now.year)
        self.start_month = ctk.IntVar(value=now.month)
        self.start_day = ctk.IntVar(value=now.day)
        
        self.end_year = ctk.IntVar(value=now.year)
        self.end_month = ctk.IntVar(value=now.month)
        self.end_day = ctk.IntVar(value=now.day)
    
    def refresh_metrics(self):
        if not self.metrics_controller:
            for label in self.metric_labels.values():
                label.configure(text="-")
            return

        data = self.metrics_controller.get_summary(start=self.active_start_date, end=self.active_end_date)


        self.metric_labels["avg_wait"].configure(text=data["avg_wait"])
        self.metric_labels["avg_provider"].configure(text=data["avg_provider"])
        self.metric_labels["avg_cleaning"].configure(text=data["avg_cleaning"])
        self.metric_labels["turnovers"].configure(text=str(data["turnovers"]))
        self.metric_labels["stuck_rooms"].configure(text=", ".join(map(str, data["stuck_rooms"])) or "-")
        
    def apply_date_range(self):
        try:
            start = datetime(
                self.start_year.get(),
                self.start_month.get(),
                self.start_day.get()
            )

            end = datetime(
                self.end_year.get(),
                self.end_month.get(),
                self.end_day.get()
            ) + timedelta(days=1)  # inclusive end date

            start = datetime(self.start_year.get(), self.start_month.get(), self.start_day.get())
            end = datetime(self.end_year.get(), self.end_month.get(), self.end_day.get()) + timedelta(days=1)

            if start > end:
                self.active_start_date = None
                self.active_end_date = None
                return

            self.active_start_date = start.isoformat()
            self.active_end_date = end.isoformat()

        except ValueError:
            self.active_start_date = None
            self.active_end_date = None
        
    def clear_rooms(self):
        for tile in self.room_tiles:
            tile.destroy()
        self.room_tiles = []

    def reload_rooms(self):
        self.clear_rooms()

        if not self.controller:
            return

        rooms = self.controller.get_all_rooms()
        rooms.sort(key=lambda r: (STATUS_PRIORITY.get(RoomStatus(r["status"]), 99), r["name"]))

        for idx, room in enumerate(rooms):
            tile = RoomTile(self.scrollable_frame, room, self.controller)
            tile.grid(row=idx // 4, column=idx % 4, padx=10, pady=10)
            self.room_tiles.append(tile)

    def refresh_tiles(self):
        if not self.controller:
            return
        
        rooms = self.controller.get_all_rooms()
        rooms.sort(key=lambda r: (STATUS_PRIORITY.get(RoomStatus(r["status"]), 99), r["name"]))

        room_map = {tile.room["id"]: tile for tile in self.room_tiles}

        if len(room_map) != len(rooms) or any(room["id"] not in room_map for room in rooms):
            self.reload_rooms()
            return


        for idx, room in enumerate(rooms):
            tile = room_map[room["id"]]
            tile.room = room
            tile.refresh()
            tile.grid(row=idx // 4, column=idx % 4)

    def auto_refresh(self):
        self.refresh_tiles()
        self.refresh_metrics()
        self.after(1000, self.auto_refresh)

# ----------------------------
# Run the app
# ----------------------------
if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
