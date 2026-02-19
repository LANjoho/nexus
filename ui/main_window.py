import customtkinter as ctk
from tkinter import messagebox
from controllers.room_controller import RoomController
from database.db import Database
from models.enums import RoomStatus, UpdateSource
from controllers.metrics_controller import MetricsController
from datetime import datetime, timedelta

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
    RoomStatus.OUT_OF_SERVICE: "#FFFFFF"   # White
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
        self.name_label.grid(row=0, column=0, columnspan=3, pady=(5,0))

        # Status Label
        self.status_label = ctk.CTkLabel(
            self,
            text=room["status"],
            fg_color=STATUS_COLORS.get(RoomStatus(room["status"]), "#FFFFFF"),
            corner_radius=5
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
                command=lambda s=status: self.update_status(s)
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
        self.room = room_dict[self.room["id"]]
        self.status_label.configure(
            text=self.room["status"],
            fg_color=STATUS_COLORS.get(RoomStatus(self.room["status"]), "#CCCCCC")
        )
class MainWindow(ctk.CTk):
    def __init__(self, controller):
        super().__init__()
        self.title("Clinical Room Manager")
        self.geometry("800x600")
        self.controller = controller
        
        self.metrics_controller = MetricsController(controller.db)
        
        self.active_start_date = None
        self.active_end_date = None
        
        # Tabs
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.rooms_tab = self.tabs.add("Rooms")
        self.metrics_tab = self.tabs.add("Metrics")
        
        # Scrollable Frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self.rooms_tab)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.room_tiles = []
        self.load_rooms()
        
        self.metric_labels = {}
        
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
            return ctk.CTkOptionMenu(
                parent,
                values=[str(v).zfill(2) for v in values],
                variable=var
            )

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

        # Apply button
        ctk.CTkButton(
            date_frame,
            text="Apply",
            command=self.apply_date_filter
        ).grid(row=0, column=4, rowspan=2, padx=15)

        
        '''
        OLD VERSION:
        range_frame = ctk.CTkFrame(metrics_frame)
        range_frame.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))

        ctk.CTkLabel(range_frame, text="From:").grid(row=0, column=0, padx=(0, 5))
        self.start_date_entry = ctk.CTkEntry(
            range_frame,
            placeholder_text="YYYY-MM-DD",
            width=120
        )
        self.start_date_entry.grid(row=0, column=1, padx=(0, 15))

        ctk.CTkLabel(range_frame, text="To:").grid(row=0, column=2, padx=(0, 5))
        self.end_date_entry = ctk.CTkEntry(
            range_frame,
            placeholder_text="YYYY-MM-DD",
            width=120
        )
        self.end_date_entry.grid(row=0, column=3, padx=(0, 15))

        self.apply_range_btn = ctk.CTkButton(
            range_frame,
            text="Apply",
            width=80,
            command=self.apply_date_range
        )
        self.apply_range_btn.grid(row=0, column=4)
        '''
        
        #--- Metric Labels ---
        
        def add_metric(key, label, row):
            title = ctk.CTkLabel(metrics_frame, text=label, font=("Arial", 16, "bold"))
            title.grid(row=row +1, column=0, sticky="w", pady=10)

            value = ctk.CTkLabel(metrics_frame, text="-", font=("Arial", 16))
            value.grid(row=row +1, column=1, sticky="w", pady=10)

            self.metric_labels[key] = value

        add_metric("avg_wait", "Average Waiting Time:", 0)
        add_metric("avg_provider", "Average Seeing Provider Time:", 1)
        #add_metric("avg_occupied", "Average Occupied Time:", 0)
        add_metric("avg_cleaning", "Average Cleaning Time:", 2)
        add_metric("turnovers", "Total Turnovers:", 3)
        add_metric("stuck_rooms", "Rooms Stuck Needing Cleaning:", 4)

        
        # Start auto-refresh loop (must be at the end of __init__)
        self.auto_refresh()
    

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
        data = self.metrics_controller.get_summary(
            start=self.active_start_date,
            end=self.active_end_date
        )

        #self.metric_labels["avg_occupied"].configure(text=data["avg_occupied"])
        self.metric_labels["avg_wait"].configure(text=data["avg_wait"])
        self.metric_labels["avg_provider"].configure(text=data["avg_provider"])
        self.metric_labels["avg_cleaning"].configure(text=data["avg_cleaning"])
        self.metric_labels["turnovers"].configure(text=str(data["turnovers"]))
        self.metric_labels["stuck_rooms"].configure(
            text=", ".join(map(str, data["stuck_rooms"])) or "-"
        )
        
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

            if start > end:
                self.active_start_date = None
                self.active_end_date = None
                return

            self.active_start_date = start.isoformat()
            self.active_end_date = end.isoformat()

        except ValueError:
            self.active_start_date = None
            self.active_end_date = None
        
    def load_rooms(self):
        rooms = self.controller.get_all_rooms()

        # Sort by priority, then room name
        rooms.sort(
            key=lambda r: (
                STATUS_PRIORITY.get(RoomStatus(r["status"]), 99),
                r["name"]
            )
        )

        for idx, room in enumerate(rooms):
            tile = RoomTile(self.scrollable_frame, room, self.controller)
            tile.grid(row=idx // 4, column=idx % 4, padx=10, pady=10)
            self.room_tiles.append(tile)

    def refresh_tiles(self):
        rooms = self.controller.get_all_rooms()

        # Sort again on refresh
        rooms.sort(
            key=lambda r: (
                STATUS_PRIORITY.get(RoomStatus(r["status"]), 99),
                r["name"]
            )
        )

        room_map = {tile.room["id"]: tile for tile in self.room_tiles}

        for idx, room in enumerate(rooms):
            tile = room_map[room["id"]]
            tile.room = room
            tile.refresh()
            tile.grid(row=idx // 4, column=idx % 4)

    def auto_refresh(self):
        self.refresh_tiles()
        self.refresh_metrics()
        self.after(1000, self.auto_refresh)  # refresh every 1 second


# ----------------------------
# Run the app
# ----------------------------
if __name__ == "__main__":
    app = MainWindow(controller)
    app.mainloop()
