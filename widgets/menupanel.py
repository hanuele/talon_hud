from talon import skia, ui, cron, actions, clip
from talon.skia import Path
from talon.types import Point2d as Point2d
from user.talon_hud.layout_widget import LayoutWidget
from user.talon_hud.widget_preferences import HeadUpDisplayUserWidgetPreferences
from user.talon_hud.utils import layout_rich_text, remove_tokens_from_rich_text, linear_gradient, hit_test_rect
from user.talon_hud.content.typing import HudRichTextLine, HudPanelContent, HudButton, HudIcon
import collections
import math

from dataclasses import dataclass
from typing import Callable, Any

@dataclass
class HeadUpMenuItem:
    id: str
    text: str
    image: str
    menu_items: list
    context_options: list
    callback: Callable[[Any, Any], None]

@dataclass
class Option:
    id: str
    text: str
    callback: Callable[[Any, Any], None]

@dataclass
class Hex:
    q: int
    r: int
    s: int

@dataclass
class Orientation:
    f0:float
    f1:float
    f2:float
    f3:float
    b0:float
    b1:float
    b2:float
    b3:float
    start_angle: float

@dataclass
class Layout:
    orientation:Orientation
    size: float
    origin:float

@dataclass
class OffsetCoord:
    col: int
    row: int

def click_callback(item: HeadUpMenuItem):
    print( "CLICKED MENU ITEM " + item.id )

EVEN = 1
ODD = -1
layout_pointy = Orientation(math.sqrt(3.0), math.sqrt(3.0) / 2.0, 0.0, 3.0 / 2.0, math.sqrt(3.0) / 3.0, -1.0 / 3.0, 0.0, 2.0 / 3.0, 0.5)
layout_flat = Orientation(3.0 / 2.0, 0.0, math.sqrt(3.0) / 2.0, math.sqrt(3.0), 2.0 / 3.0, 0.0, -1.0 / 3.0, math.sqrt(3.0) / 3.0, 0.0)

class HeadUpMenuPanel(LayoutWidget):
    preferences = HeadUpDisplayUserWidgetPreferences(type="menu_panel", x=200, y=50, width=80, height=80, limit_x=200, limit_y=400, limit_width=800, limit_height=400, enabled=True, alignment="left", expand_direction="down", font_size=12)
    mouse_enabled = True

    line_padding = 6
    
    buttons = []
    menu_items = []
    item_hovered = -1
    
    subscribed_content = ["mode"]
    content = {
        'mode': 'command',
        'menu_items': [
            HeadUpMenuItem('1.', '\n     1.!', 'de_DE', [
                HeadUpMenuItem('1.1', ' <*"1.1"/>', '', [
                    HeadUpMenuItem('1.1.1', ' <*1.1.1/> und       <*wieso/>', '', [
                        HeadUpMenuItem('1.1.1.1', 'Ich weiß es     </1.1.1.1/>', '', [
                        
                        ], [],click_callback),
                        HeadUpMenuItem('1.1.1.2', '1.1.1.2', '', [
                            HeadUpMenuItem('1.1.1.2.1', '1.1.1.2.1', '', [
                            
                            ], [],click_callback)
                        ], [],click_callback),
                        HeadUpMenuItem('1.1.1.3', '1.1.1.3', '', [
                           HeadUpMenuItem('1.1.1.3.1', '1.1.1.3.1', '', [
                               HeadUpMenuItem('1.1.1.3.1.1', '1.1.1.3.1.1', '', [
                            
                                ], [],click_callback) 
                            ], [],click_callback)  
                        ], [],click_callback)
                    ], [],click_callback)
                ], [],click_callback)
            ], [],click_callback)
        ]
    }
    
    panel_content = HudPanelContent('thisdoesnothing', 'asdf', ['content'], [], 0, False)

    def set_preference(self, preference, value, persisted=False):
        self.mark_layout_invalid = True
        super().set_preference(preference, value, persisted)

    def on_mouse(self, event):
        item_hovered = -1
        for index, item in enumerate(self.menu_items):
            flat = Layout(layout_pointy, Point2d(40,40), Point2d(self.x, self.y))
            
            h = self.pixel_to_hex(flat, event.gpos)
            h.q = math.floor(h.q)
            h.r = math.floor(h.r)
            h.s = math.floor(h.s)
            #print(h)
            #self.panel_content.content = h
            #print(self.panel_content.content) 
            
            #if hit_test_rect(item['rect'], event.gpos):
            #    item_hovered = index
            #    break
            if (h.q == item['hex'].q and h.r == item['hex'].r):
                item_hovered = index
                #print(h)
                #print(item['hex'])
                break
        
        if item_hovered != self.item_hovered:
           self.item_hovered = item_hovered
           self.canvas.resume()
        
        if event.event == "mouseup" and event.button == 0:
            clicked_item = None
            if item_hovered != -1:
                clicked_item = self.menu_items[item_hovered]
                
            if clicked_item != None:
                self.item_hovered = -1
                clicked_item['selected'] = True
                
                clicked_item['item'].callback(clicked_item['item'])
                for index_, item_ in enumerate(self.menu_items):
                    parent_col = self.roffset_from_cube(ODD,item['hex']).col
                    parent_row = self.roffset_from_cube(ODD,item['hex']).row
                    item_col = self.roffset_from_cube(ODD,item_['hex']).col
                    item_row = self.roffset_from_cube(ODD,item_['hex']).row

                    if  parent_row == item_row-1 :
                        self.menu_items[index_]['visible'] = True

        if event.button == 1 and event.event == "mouseup":
            self.event_dispatch.show_context_menu(self.id, event.gpos, self.buttons)

        if event.button == 0 and event.event == "mouseup":
            self.event_dispatch.hide_context_menu()

        # Allow dragging and dropping with the mouse
        if item_hovered == -1:
            super().on_mouse(event)

    
    def layout_content(self, canvas, paint):
        paint.textsize = self.font_size
        
        horizontal_alignment = "right" if self.limit_x < self.x else "left"
        vertical_alignment = "bottom" if self.limit_y < self.y else "top"
    
        hexagon_size = 80
        
        self.menu_items = []

        hover_padding = 40
        x = self.x - hover_padding - hexagon_size
        y = self.y - hover_padding - hexagon_size
        self.layout_menu_items(paint, hexagon_size, self.content["menu_items"],OffsetCoord(0,0))
        #complete_click_rect = ui.Rect(self.x, self.y, 1000,1000)
        complete_click_rect = ui.Rect(self.x, self.y, hover_padding + len(self.menu_items) * hexagon_size,  hover_padding + len(self.menu_items) * hexagon_size)

        return [{
            "rect": complete_click_rect,
            "items": self.menu_items
        }]
    
    # Recursively go through the menu items
    def layout_menu_items(self, paint, hexagon_size: int, menu_items: list[HeadUpMenuItem],offsetCoord:OffsetCoord):
        for menu_item in menu_items:
            print(offsetCoord)
            placed_menu_item = self.layout_menu_item(paint, hexagon_size, menu_item, offsetCoord)
            
            self.menu_items.append(placed_menu_item)
            print(menu_item.id)
            if len(menu_item.menu_items) > 0:  
                newOffsetCoord = OffsetCoord(offsetCoord.col,offsetCoord.row+1)
                self.layout_menu_items(paint, hexagon_size, menu_item.menu_items, newOffsetCoord)
            offsetCoord.col +=1
            
        
    def layout_menu_item(self, paint, hexagon_size: int, menu_item: HeadUpMenuItem,offsetCoord: OffsetCoord):
        h = self.roffset_to_cube(ODD, offsetCoord)        
        flat = Layout(layout_pointy, Point2d(hexagon_size/2,hexagon_size/2), Point2d(self.x, self.y))
        hex_coord = self.hex_to_pixel(flat, h) 
        return {
            "rect": ui.Rect(hex_coord.x, hex_coord.y, hexagon_size, hexagon_size),
            "item": menu_item,
            "text": layout_rich_text(paint, menu_item.text, hexagon_size - 10, hexagon_size),
            "coord": offsetCoord,
            "hex": h,
            "selected": False,
            "visible": (h.q == 0 and h.r == 0)
        }

        
    def draw_content(self, canvas, paint, dimensions) -> bool:
        paint.textsize = self.font_size
        
        paint.style = paint.Style.FILL
        for index, menu_item in enumerate(dimensions["items"]):
            if menu_item["visible"]:
                self.draw_menu_item(canvas, paint, menu_item, index == self.item_hovered)
        
        return False


    def qoffset_from_cube(self, offset, h):
        col = h.q
        row = h.r + (h.q + offset * (h.q & 1)) // 2
        if offset != EVEN and offset != ODD:
            raise ValueError("offset must be EVEN (+1) or ODD (-1)")
        return OffsetCoord(col, row)

    def qoffset_to_cube(self, offset, h):
        q = h.col
        r = h.row - (h.col + offset * (h.col & 1)) // 2
        s = -q - r
        if offset != EVEN and offset != ODD:
            raise ValueError("offset must be EVEN (+1) or ODD (-1)")
        return Hex(q, r, s)

    def roffset_from_cube(self, offset, h):
        col = h.q + (h.r + offset * (h.r & 1)) // 2
        row = h.r
        if offset != EVEN and offset != ODD:
            raise ValueError("offset must be EVEN (+1) or ODD (-1)")
        return OffsetCoord(col, row)

    def roffset_to_cube(self, offset, h):
        q = h.col - (h.row + offset * (h.row & 1)) // 2
        r = h.row
        s = -q - r
        if offset != EVEN and offset != ODD:
            raise ValueError("offset must be EVEN (+1) or ODD (-1)")
        return Hex(q, r, s)
  

    def hex_to_pixel(self,layout, h) -> Point2d:
        M = layout.orientation
        size = layout.size
        origin = layout.origin
        x = (M.f0 * h.q + M.f1 * h.r) * size.x
        y = (M.f2 * h.q + M.f3 * h.r) * size.y
        return Point2d(x + origin.x, y + origin.y)

    def pixel_to_hex(self,layout, p) -> Hex:
        M = layout.orientation
        size = layout.size
        origin = layout.origin
        pt = Point2d((p.x - origin.x) / size.x, (p.y - origin.y) / size.y)
        q = M.b0 * pt.x + M.b1 * pt.y
        r = M.b2 * pt.x + M.b3 * pt.y
        return Hex(q, r, -q - r)

    def hex_corner_offset(self,layout, corner) -> Point2d:
        M = layout.orientation
        size = layout.size
        angle = 2.0 * math.pi * (M.start_angle - corner) / 6.0
        return Point2d(size.x * math.cos(angle), size.y * math.sin(angle))

    def polygon_corners(self,layout, h) -> Path:
        corners = []
        center = self.hex_to_pixel(layout, h)
        path = Path()

        for i in range(0, 7):
            offset = self.hex_corner_offset(layout, i)
            if i == 0: 
                path.move_to(center.x + offset.x, center.y + offset.y)
            else:
                path.line_to(center.x + offset.x, center.y + offset.y)
            
        return path

    
    def drawHex(self,canvas,center,dimensions):
        """Draws a hex"""
        flat = Layout(layout_pointy, dimensions, Point2d(0, 0))
        h = self.pixel_to_hex(flat, center)
        canvas.draw_path(self.polygon_corners(flat, h))
      

    def draw_menu_item(self, canvas, paint, placed_menu_item, hovered):
        """Draws the menu item"""
        paint.textsize = self.font_size
        
        paint.color = '00AA00' if not hovered else '00FF00'
        
        center = Point2d(placed_menu_item['rect'].x + placed_menu_item['rect'].width/ 2,\
            placed_menu_item['rect'].y + placed_menu_item['rect'].height/ 2)
        dimensions = Point2d(placed_menu_item['rect'].height/ 2, placed_menu_item['rect'].height /2)
        self.drawHex(canvas,center,dimensions)
        #canvas.draw_rect( placed_menu_item['rect'] ) 
        y = placed_menu_item['rect'].y
        image_radius = 40
        if (placed_menu_item['item'].image != '' and self.theme.get_image(placed_menu_item['item'].image) is not None ):
            image = self.theme.get_image(placed_menu_item['item'].image, image_radius, image_radius)
            canvas.draw_image(image, placed_menu_item['rect'].x + image_radius - image.width / 2, placed_menu_item['rect'].y + 10 )
            y += self.font_size
        
        text_x = placed_menu_item['rect'].x + 10
        
        text_height_offset = len([line for line in placed_menu_item['text'] if line.x == 0]) * self.font_size / 2        
        text_y = y + placed_menu_item['rect'].height / 2 - text_height_offset
        
        paint.color = '000000'
        self.draw_rich_text(canvas, paint, placed_menu_item['text'], text_x, text_y, self.line_padding)
  

    
    

