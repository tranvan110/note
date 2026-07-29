# $date
#    Tue Jul 28 17:57:00 2026
# $end
# $version
#    Icarus Verilog
# $end
# $timescale
#    1ns
# $end
# $scope module top $end
# $var reg 1 ! clk $end
# $var reg 1 " rst $end
# $var reg 4 # data [3:0] $end
# $upscope $end
# $enddefinitions $end

# $dumpvars
# bxxxx #
# x"
# x!
# $end

# #0
# 1"
# 0!
# b0000 #

# #10
# 0"

# #20
# 1!
# b0101 #

# #30
# 0!


import sys
import re

def parse_vcd_header(lines):
    """
    Hàm đọc phần khai báo (Header) của file VCD để lấy timescale và ánh xạ mã ký tự -> tên tín hiệu.
    """
    signals = {}  # Lưu trữ: {mã_ký_tự: {'name': tên, 'size': độ_rộng, 'type': kiểu}}
    timescale = "1ns"
    
    content = "".join(lines)
    # Tìm timescale
    timescale_match = re.search(r'\$timescale\s+(.*?)\s+\$end', content, re.DOTALL)
    if timescale_match:
        timescale = timescale_match.group(1).strip()

    # Tìm tất cả các khai báo biến $var
    var_matches = re.findall(r'\$var\s+(\w+)\s+(\d+)\s+(\S+)\s+(\S+).*?\$end', content)
    for var_type, size, sym, name in var_matches:
        signals[sym] = {
            'name': name,
            'size': int(size),
            'type': var_type,
            'data': []  # Sẽ dùng để lưu lịch sử thay đổi: (thời_gian, giá_trị)
        }
        
    return signals, timescale

def parse_vcd_data(lines, signals):
    """
    Hàm đọc phần dữ liệu thay đổi của các tín hiệu theo thời gian.
    """
    current_time = 0
    in_data_section = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Bắt đầu phần dữ liệu khi gặp $enddefinitions hoặc $dumpvars
        if "$enddefinitions" in line or "$dumpvars" in line:
            in_data_section = True
            continue
            
        if not in_data_section:
            continue
            
        # Nếu dòng bắt đầu bằng #, đó là mốc thời gian mới
        if line.startswith('#'):
            current_time = int(line[1:])
            continue
            
        # Bỏ qua các từ khóa kết thúc của VCD trong phần data
        if line.startswith('$'):
            continue
            
        # Xử lý giá trị thay đổi
        if line.startswith('b') or line.startswith('B'):
            # Tín hiệu nhiều bit (Vector). Ví dụ: b0101 #
            parts = line.split()
            if len(parts) == 2:
                val, sym = parts[0][1:], parts[1]
                if sym in signals:
                    signals[sym]['data'].append((current_time, val))
        else:
            # Tín hiệu 1-bit. Ví dụ: 1! hoặc x"
            val = line[0]
            sym = line[1:]
            if sym in signals:
                signals[sym]['data'].append((current_time, val))
                
    return signals

def calculate_max_time(signals):
    """
    Tìm mốc thời gian lớn nhất xuất hiện trong mô phỏng để tính độ rộng trục X.
    """
    max_time = 0
    for sym, info in signals.items():
        if info['data']:
            last_time = info['data'][-1][0]
            if last_time > max_time:
                max_time = last_time
    return max_time if max_time > 0 else 100

def generate_svg_waveform(signals, max_time, timescale):
    """
    Hàm vẽ đồ thị dạng SVG từ dữ liệu đã parse.
    Trả về chuỗi văn bản chứa nội dung file SVG.
    """
    # Cấu hình các thông số đồ họa cơ bản (Pixel)
    X_SCALE = 2          # 1 đơn vị thời gian VCD = 2 pixel trục X
    ROW_HEIGHT = 60       # Chiều cao dành cho mỗi hàng tín hiệu
    SIGNAL_HEIGHT = 30    # Chiều cao thực tế của dạng sóng 1 hàng
    PADDING_LEFT = 120    # Khoảng trống bên trái để hiển thị tên tín hiệu
    PADDING_TOP = 40      # Khoảng trống phía trên
    
    num_signals = len(signals)
    svg_width = PADDING_LEFT + (max_time * X_SCALE) + 50
    svg_height = PADDING_TOP + (num_signals * ROW_HEIGHT) + 40
    
    # Khởi tạo chuỗi SVG header
    svg_lines = [
        f'<svg xmlns="http://w3.org" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">',
        '  <style>',
        '    .label { font-family: monospace; font-size: 14px; fill: #333; }',
        '    .time-label { font-family: monospace; font-size: 11px; fill: #888; }',
        '    .grid { stroke: #ddd; stroke-dasharray: 2,2; stroke-width: 1; }',
        '    .wave-1bit { stroke: #00aa00; stroke-width: 2; fill: none; }',
        '    .wave-bus { stroke: #0055ff; stroke-width: 2; fill: none; }',
        '    .wave-bus-text { font-family: monospace; font-size: 10px; fill: #0055ff; text-anchor: middle; }',
        '  </style>',
        '  <!-- Background -->',
        f'  <rect width="100%" height="100%" fill="#fafafa"/>'
    ]
    
    # Vẽ các mốc thời gian và đường lưới dọc (Grid)
    step = max(1, max_time // 10)  # Tự động chia tối đa 10 vạch thời gian
    for t in range(0, max_time + 1, step):
        x = PADDING_LEFT + (t * X_SCALE)
        svg_lines.append(f'  <line x1="{x}" y1="{PADDING_TOP}" x2="{x}" y2="{svg_height - 40}" class="grid"/>')
        svg_lines.append(f'  <text x="{x}" y="{PADDING_TOP - 10}" class="time-label" text-anchor="middle">{t} {timescale}</text>')

    # Vẽ từng tín hiệu
    for idx, (sym, info) in enumerate(signals.items()):
        y_offset = PADDING_TOP + (idx * ROW_HEIGHT)
        y_high = y_offset + (ROW_HEIGHT - SIGNAL_HEIGHT) // 2
        y_low = y_high + SIGNAL_HEIGHT
        y_mid = y_high + (SIGNAL_HEIGHT // 2)
        
        # Ghi tên tín hiệu ở cột bên trái
        svg_lines.append(f'  <text x="20" y="{y_mid + 5}" class="label">{info["name"]}</text>')
        
        history = info['data']
        if not history:
            continue
            
        # Thêm mốc kết thúc ảo để nét vẽ kéo dài đến cuối đồ thị
        if history[-1][0] < max_time:
            history.append((max_time, history[-1][1]))
            
        if info['size'] == 1:
            # === VẼ TÍN HIỆU 1-BIT ===
            path_points = []
            prev_x = PADDING_LEFT + (history[0][0] * X_SCALE)
            prev_y = y_low if history[0][1] == '0' else y_high
            path_points.append(f"M {prev_x} {prev_y}")
            
            for t, val in history[1:]:
                x = PADDING_LEFT + (t * X_SCALE)
                # Vẽ ngang tới mốc thời gian mới
                path_points.append(f"H {x}")
                # Xác định mức logic mới
                curr_y = y_low if val == '0' else (y_high if val == '1' else y_mid)
                # Vẽ đứng để chuyển trạng thái
                path_points.append(f"V {curr_y}")
                
            path_str = " ".join(path_points)
            svg_lines.append(f'  <path d="{path_str}" class="wave-1bit"/>')
            
        else:
            # === VẼ TÍN HIỆU BUS (NHIỀU BIT) ===
            # Bus thường được vẽ dạng các ô lục giác liên tiếp (hoặc đan chéo)
            for i in range(len(history) - 1):
                t_curr, val_curr = history[i]
                t_next, _ = history[i+1]
                
                x_start = PADDING_LEFT + (t_curr * X_SCALE)
                x_end = PADDING_LEFT + (t_next * X_SCALE)
                
                if x_start == x_end:
                    continue
                
                # Tạo hình hộp bao quanh giá trị Bus (vát 2 đầu nếu có thể, ở đây vẽ hình chữ nhật đơn giản)
                svg_lines.append(f'  <path d="M {x_start} {y_high} L {x_end} {y_high} L {x_end} {y_low} L {x_start} {y_low} Z" class="wave-bus"/>')
                
                # Hiển thị giá trị text ở giữa ô nếu ô đủ rộng
                if (x_end - x_start) > 40:
                    x_mid = (x_start + x_end) / 2
                    svg_lines.append(f'  <text x="{x_mid}" y="{y_mid + 4}" class="wave-bus-text">{val_curr}</text>')

    svg_lines.append('</svg>')
    return "\n".join(svg_lines)

def convert_vcd_to_svg(vcd_filename, svg_filename):
    """
    Hàm tổng hợp quy trình đọc file và xuất file.
    """
    try:
        with open(vcd_filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file {vcd_filename}")
        return

    # Bước 1: Phân tích Header
    signals, timescale = parse_vcd_header(lines)
    
    # Bước 2: Phân tích Dữ liệu sóng
    signals = parse_vcd_data(lines, signals)
    
    # Bước 3: Tính toán khoảng thời gian lớn nhất
    max_time = calculate_max_time(signals)
    
    # Bước 4: Tạo chuỗi định dạng SVG
    svg_content = generate_svg_waveform(signals, max_time, timescale)
    
    # Bước 5: Ghi ra file SVG
    with open(svg_filename, 'w', encoding='utf-8') as f:
        f.write(svg_content)
        
    print(f"Chuyển đổi thành công! File SVG đã được lưu tại: {svg_filename}")

# Điểm chạy chương trình
if __name__ == "__main__":
    # Thay đổi đường dẫn file thực tế của bạn tại đây
    input_vcd = "simulation.vcd"
    output_svg = "waveform.svg"
    
    convert_vcd_to_svg(input_vcd, output_svg)



##########################################################################################


import sys
import re

def parse_vcd_header(lines):
    """
    Hàm đọc phần khai báo (Header) của file VCD để lấy timescale và ánh xạ mã ký tự -> tên tín hiệu.
    """
    signals = {}
    timescale = "1ns"
    content = "".join(lines)
    
    timescale_match = re.search(r'\$timescale\s+(.*?)\s+\$end', content, re.DOTALL)
    if timescale_match:
        timescale = timescale_match.group(1).strip()

    var_matches = re.findall(r'\$var\s+(\w+)\s+(\d+)\s+(\S+)\s+(\S+).*?\$end', content)
    for var_type, size, sym, name in var_matches:
        signals[sym] = {
            'name': name,
            'size': int(size),
            'type': var_type,
            'data': []
        }
    return signals, timescale

def parse_vcd_data(lines, signals):
    """
    Hàm đọc phần dữ liệu thay đổi của các tín hiệu theo thời gian.
    """
    current_time = 0
    in_data_section = False
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('$'):
            if "$enddefinitions" in line or "$dumpvars" in line:
                in_data_section = True
            continue
            
        if not in_data_section:
            continue
            
        if line.startswith('#'):
            current_time = int(line[1:])
            continue
            
        if line.startswith('b') or line.startswith('B'):
            parts = line.split()
            if len(parts) == 2:
                val, sym = parts[0][1:], parts[1]
                if sym in signals:
                    signals[sym]['data'].append((current_time, val.lower()))
        else:
            val = line[0].lower()
            sym = line[1:]
            if sym in signals:
                signals[sym]['data'].append((current_time, val))
                
    return signals

def calculate_max_time(signals):
    """
    Tìm mốc thời gian lớn nhất xuất hiện trong mô phỏng để tính độ rộng trục X.
    """
    max_time = 0
    for sym, info in signals.items():
        if info['data']:
            last_time = info['data'][-1][0]
            if last_time > max_time:
                max_time = last_time
    return max_time if max_time > 0 else 100

def draw_1bit_signal(history, max_time, x_scale, padding_left, y_high, y_mid, y_low):
    """
    Hàm chuyên biệt để tạo thẻ SVG <path> cho tín hiệu 1-bit, xử lý chính xác 0, 1, x, z.
    """
    if not history:
        return ""
        
    # Tạo bản sao và thêm mốc thời gian ảo ở cuối để kéo dài nét vẽ tới hết đồ thị
    points = list(history)
    if points[-1][0] < max_time:
        points.append((max_time, points[-1][1]))
        
    svg_paths = []
    
    # Định nghĩa hàm lấy tọa độ Y dựa trên trạng thái logic
    def get_y_coords(state):
        if state == '1': return [y_high]
        if state == '0': return [y_low]
        if state == 'z': return [y_mid]
        if state == 'x': return [y_high, y_low] # Trạng thái X cần cả biên trên và dưới
        return [y_mid] # Mặc định nếu có lỗi dữ liệu

    # Duyệt qua các phân đoạn thời gian để vẽ từng đoạn (Segment-by-Segment)
    for i in range(len(points) - 1):
        t_curr, val_curr = points[i]
        t_next, _ = points[i+1]
        
        x_start = padding_left + (t_curr * x_scale)
        x_end = padding_left + (t_next * x_scale)
        
        if x_start == x_end:
            continue
            
        y_starts = get_y_coords(val_curr)
        
        if val_curr in ['0', '1', 'z']:
            # Vẽ đường thẳng đơn thông thường (Xanh lá cho 0/1, Xám cho Z)
            cls = "wave-z" if val_curr == 'z' else "wave-1bit"
            path_str = f"M {x_start} {y_starts[0]} L {x_end} {y_starts[0]}"
            svg_paths.append(f'  <path d="{path_str}" class="{cls}"/>')
            
        elif val_curr == 'x':
            # Vẽ trạng thái X: Hình hộp đóng kín (kết hợp cả đường trên và đường dưới) kèm gạch chéo chập chững
            path_str = f"M {x_start} {y_high} L {x_end} {y_high} L {x_end} {y_low} L {x_start} {y_low} Z"
            svg_paths.append(f'  <path d="{path_str}" class="wave-x-box"/>')
            # Vẽ thêm các đường gạch chéo tạo hiệu ứng "hỗn loạn" đặc trưng của X nếu đoạn đủ rộng
            if (x_end - x_start) >= 10:
                svg_paths.append(f'  <line x1="{x_start}" y1="{y_low}" x2="{x_end}" y2="{y_high}" class="wave-x-line"/>')
                svg_paths.append(f'  <line x1="{x_start}" y1="{y_high}" x2="{x_end}" y2="{y_low}" class="wave-x-line"/>')
                
        # Vẽ đường chuyển tầng (Vertical transition) thẳng đứng nối liền giữa đoạn cũ và đoạn mới
        if i < len(points) - 2:
            _, val_next = points[i+1]
            y_ends = get_y_coords(val_next)
            
            # Chỉ vẽ đường nối dọc nếu hai trạng thái liền kề không phải là X 
            # (Vì X đã tự đóng khung vuông bằng các đường dựng dọc sẵn rồi)
            if val_curr != 'x' and val_next != 'x':
                path_str = f"M {x_end} {y_starts[0]} L {x_end} {y_ends[0]}"
                svg_paths.append(f'  <path d="{path_str}" class="wave-transition"/>')
                
    return "\n".join(svg_paths)

def generate_svg_waveform(signals, max_time, timescale):
    """
    Hàm dựng giao diện SVG và tổng hợp các cấu trúc đường vẽ.
    """
    X_SCALE = 3           # Tăng độ rộng một chút để nhìn rõ các đoạn ngắn
    ROW_HEIGHT = 70       
    SIGNAL_HEIGHT = 30    
    PADDING_LEFT = 130    
    PADDING_TOP = 50      
    
    num_signals = len(signals)
    svg_width = PADDING_LEFT + (max_time * X_SCALE) + 50
    svg_height = PADDING_TOP + (num_signals * ROW_HEIGHT) + 40
    
    svg_lines = [
        f'<svg xmlns="http://w3.org" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">',
        '  <style>',
        '    .label { font-family: monospace; font-size: 14px; font-weight: bold; fill: #2c3e50; }',
        '    .time-label { font-family: monospace; font-size: 11px; fill: #7f8c8d; }',
        '    .grid { stroke: #ecf0f1; stroke-dasharray: 3,3; stroke-width: 1; }',
        '    .wave-1bit { stroke: #27ae60; stroke-width: 2.5; fill: none; stroke-linecap: round; }',
        '    .wave-z { stroke: #95a5a6; stroke-width: 2; stroke-dasharray: 4,2; fill: none; }',
        '    .wave-x-box { fill: #fadbd8; stroke: #e74c3c; stroke-width: 1.5; }',
        '    .wave-x-line { stroke: #e74c3c; stroke-width: 1; stroke-opacity: 0.7; }',
        '    .wave-transition { stroke: #bdc3c7; stroke-width: 1.5; fill: none; }',
        '    .wave-bus { stroke: #2980b9; stroke-width: 2; fill: #ebf5fb; }',
        '    .wave-bus-text { font-family: monospace; font-size: 11px; fill: #2980b9; text-anchor: middle; font-weight: bold; }',
        '  </style>',
        '  <!-- Background -->',
        f'  <rect width="100%" height="100%" fill="#ffffff"/>'
    ]
    
    # Lưới thời gian
    step = max(1, max_time // 10)
    for t in range(0, max_time + 1, step):
        x = PADDING_LEFT + (t * X_SCALE)
        svg_lines.append(f'  <line x1="{x}" y1="{PADDING_TOP}" x2="{x}" y2="{svg_height - 40}" class="grid"/>')
        svg_lines.append(f'  <text x="{x}" y="{PADDING_TOP - 12}" class="time-label" text-anchor="middle">{t}{timescale}</text>')

    # Vẽ các đường tín hiệu
    for idx, (sym, info) in enumerate(signals.items()):
        y_offset = PADDING_TOP + (idx * ROW_HEIGHT)
        y_high = y_offset + (ROW_HEIGHT - SIGNAL_HEIGHT) // 2
        y_low = y_high + SIGNAL_HEIGHT
        y_mid = y_high + (SIGNAL_HEIGHT // 2)
        
        # Nhãn tên tín hiệu
        svg_lines.append(f'  <text x="20" y="{y_mid + 5}" class="label">{info["name"]}</text>')
        
        history = info['data']
        if not history:
            continue
            
        if info['size'] == 1:
            # Gọi hàm vẽ bổ trợ chuyên dụng cho 1-bit (có xử lý X, Z)
            svg_lines.append(draw_1bit_signal(history, max_time, X_SCALE, PADDING_LEFT, y_high, y_mid, y_low))
        else:
            # === VẼ TÍN HIỆU BUS ===
            if history[-1][0] < max_time:
                history.append((max_time, history[-1][1]))
                
            for i in range(len(history) - 1):
                t_curr, val_curr = history[i]
                t_next, _ = history[i+1]
                
                x_start = PADDING_LEFT + (t_curr * X_SCALE)
                x_end = PADDING_LEFT + (t_next * X_SCALE)
                
                if x_start == x_end:
                    continue
                
                # Định dạng màu sắc riêng cho Bus nếu nó mang giá trị lỗi x hoặc z toàn cục
                if 'x' in val_curr:
                    svg_lines.append(f'  <path d="M {x_start} {y_high} L {x_end} {y_high} L {x_end} {y_low} L {x_start} {y_low} Z" fill="#fadbd8" stroke="#e74c3c" stroke-width="1.5"/>')
                elif 'z' in val_curr:
                    svg_lines.append(f'  <line x1="{x_start}" y1="{y_mid}" x2="{x_end}" y2="{y_mid}" class="wave-z"/>')
                else:
                    svg_lines.append(f'  <path d="M {x_start} {y_high} L {x_end} {y_high} L {x_end} {y_low} L {x_start} {y_low} Z" class="wave-bus"/>')
                
                # Ghi text giá trị
                if (x_end - x_start) > 45 and 'z' not in val_curr:
                    x_mid = (x_start + x_end) / 2
                    txt_cls = "wave-bus-text" if 'x' not in val_curr else "wave-bus-text"
                    fill_color = "#e74c3c" if 'x' in val_curr else "#2980b9"
                    svg_lines.append(f'  <text x="{x_mid}" y="{y_mid + 4}" class="{txt_cls}" fill="{fill_color}">{val_curr.upper()}</text>')

    svg_lines.append('</svg>')
    return "\n".join(svg_lines)

def convert_vcd_to_svg(vcd_filename, svg_filename):
    """
    Hàm tổng hợp quy trình đọc file và xuất file.
    """
    try:
        with open(vcd_filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:

      
      print(f"Lỗi: Không tìm thấy file {vcd_filename}")
      return
    signals, timescale = parse_vcd_header(lines)
    signals = parse_vcd_data(lines, signals)
    max_time = calculate_max_time(signals)
    svg_content = generate_svg_waveform(signals, max_time, timescale)
    with open(svg_filename, 'w', encoding='utf-8') as f:
      f.write(svg_content)
      print(f"Chuyển đổi thành công! Trạng thái X, Z đã được tích hợp. Lưu tại: {svg_filename}")
      if name == "main":
        convert_vcd_to_svg("simulation.vcd", "waveform.svg")
