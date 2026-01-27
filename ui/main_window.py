import customtkinter as ctk
from controllers.room_controller import RoomController
from database.db import Database
from models.enums import RoomStatus, UpdateSource

# ----------------------------
# Initialize DB and controller
# ----------------------------
db = Database()
controller = RoomController(db)

# ----------------------------
# Color mapping for statuses
# ----------------------------
STATUS_COLORS = {
    RoomStatus.AVAILABLE: "#4CAF50",       # Green
    RoomStatus.OCCUPIED: "#F44336",        # Red
    RoomStatus.NEEDS_CLEANING: "#FF9800",  # Orange
    RoomStatus.CLEANING: "#2196F3",        # Blue
    RoomStatus.MAINTENANCE: "#9E9E9E",     # Gray
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

        # Scrollable Frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.room_tiles = []
        self.load_rooms()

    def load_rooms(self):
        rooms = self.controller.get_all_rooms()
        for idx, room in enumerate(rooms):
            tile = RoomTile(self.scrollable_frame, room, self.controller)
            tile.grid(row=idx // 4, column=idx % 4, padx=10, pady=10)
            self.room_tiles.append(tile)

    def refresh_tiles(self):
        for tile in self.room_tiles:
            tile.refresh()


# ----------------------------
# Run the app
# ----------------------------
if __name__ == "__main__":
    app = MainWindow(controller)
    app.mainloop()
