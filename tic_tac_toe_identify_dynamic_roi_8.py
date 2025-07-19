# 视频内版本，棋子下在棋盘后容易受环境影响而误识别，建议添加补光灯；且旋转棋盘可能编号错误，改进版本为版本9

import sensor, image, time

# 初始化摄像头
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False) # 关闭自动增益
sensor.set_auto_whitebal(False) # 关闭白平衡

# 棋盘参数
GRID_SIZE = 3              # 3x3棋盘
CELL_MARGIN = 30            # 格子检测边距
BLACK_THRESH = (0, 10, -33, 14, -10, 21)     # 黑棋颜色阈值
WHITE_THRESH = (60, 87, -10, 19, -15, 16)    # 白棋颜色阈值
BOARD_COLOR = (82, 99, -18, 13, -12, 23)  # 棋盘颜色阈值

BOARD_ROI = (70, 10, 190, 200)  # 棋盘区域
PIECE_ROI_LEFT = (10, 10, 60, 200)  # 左侧棋子区域
PIECE_ROI_RIGHT = (260, 10, 60, 200)  # 右侧棋子区域

def detect_individual_cells(img, BOARD_ROI):
    """直接检测九个棋格区域并固定编号"""
    # 寻找所有符合条件的色块（棋格背景）
    blobs = img.find_blobs([BOARD_COLOR],
                         roi=BOARD_ROI,
                         x_stride=20,
                         y_stride=20,
                         area_threshold=500,
                         merge=False)

    # print(len(blobs))
    if len(blobs) < 9:  # 至少需要检测到9个区域
        return None

    # 计算所有色块的中心点
    centers = [(b.cx(), b.cy(), b) for b in blobs]

    # 计算整体中心点（所有色块中心的平均值）
    # avg_x = sum(c[0] for c in centers) / len(centers)
    avg_y = sum(c[1] for c in centers) / len(centers)

    # 将色块分为三个垂直区域（上、中、下）
    vertical_sections = [[], [], []]
    for cx, cy, b in centers:
        # 根据y坐标与平均y坐标的关系确定垂直位置
        if cy < avg_y - 15:  # 上区
            vertical_sections[0].append((cx, cy, b))
        elif cy > avg_y + 15:  # 下区
            vertical_sections[2].append((cx, cy, b))
        else:  # 中区
            vertical_sections[1].append((cx, cy, b))

    # 对每个垂直区域内的色块按x坐标排序（左到右）
    for i in range(3):
        vertical_sections[i].sort(key=lambda c: c[0])

    # 确保每个垂直区域有3个色块（可能需要进行容错处理）
    rois = [[None]*GRID_SIZE for _ in range(GRID_SIZE)]
    for i in range(3):
        for j in range(min(len(vertical_sections[i]), 3)):
            cx, cy, b = vertical_sections[i][j]
            # 添加边距并确保不越界
            x = max(0, b.x() + CELL_MARGIN//2)
            y = max(0, b.y() + CELL_MARGIN//2)
            w = max(15, b.w() - 2*CELL_MARGIN)
            h = max(15, b.h() - 2*CELL_MARGIN)

            # w = max(w, h)

            # 固定编号：i=0是上区(行1)，i=1是中区(行2)，i=2是下区(行3)
            rois[i][j] = (x, y, w, h)

            # 绘制调试信息（显示1-9编号）
            cell_num = i*3 + j + 1  # 计算1-9编号
            img.draw_rectangle(x, y, w, h, color=(255, 0, 0))
            img.draw_string(x+5, y+5, str(cell_num), color=(255, 0, 0))
    return rois if all(None not in row for row in rois) else None

def detect_pieces(img, roi, threshold, piececolor):
    """检测棋子"""
    pieces = img.find_blobs([threshold],
                            roi=roi,
                            x_stride=10,
                            y_stride=10,
                            area_threshold=500,
                            merge=False)
    # 安全处理返回值
    if pieces is None:
        return []

    for piece in pieces:
        if piececolor == 1:
            img.draw_circle(piece.cx(), piece.cy(), piece.w()//2, color=(255, 0, 0))
        else:
            img.draw_circle(piece.cx(), piece.cy(), piece.w()//2, color=(0, 255, 0))

    return pieces

def detect_available_pieces(img):
    """检测两侧未下的棋子"""
    # 检测左侧区域（黑棋）
    left_circles = detect_pieces(img, PIECE_ROI_LEFT, BLACK_THRESH, piececolor = 1)
    black_pieces = len(left_circles) if left_circles else 0

    # 检测右侧区域（白棋）
    right_circles = detect_pieces(img, PIECE_ROI_RIGHT, WHITE_THRESH, piececolor = 0)
    white_pieces = len(right_circles) if right_circles else 0

    # 绘制区域标记
    img.draw_rectangle(PIECE_ROI_LEFT, color=(255, 0, 0))
    img.draw_string(PIECE_ROI_LEFT[0]+5, PIECE_ROI_LEFT[1]+5, f"b:{black_pieces}", color=(255, 0, 0))
    img.draw_rectangle(PIECE_ROI_RIGHT, color=(0, 255, 0))
    img.draw_string(PIECE_ROI_RIGHT[0]+5, PIECE_ROI_RIGHT[1]+5, f"w:{white_pieces}", color=(0, 255, 0))

    return black_pieces, white_pieces

def detect_pieces_state(img, rois):
    """检测棋子状态"""
    board = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]

    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            if rois[i][j] is None:
                continue

            x, y, w, h = rois[i][j]
            roi = (x, y, w, h)
            cell_num = i*3 + j + 1  # 计算1-9编号
            img.draw_string(x+5, y+5, str(cell_num), color=(255, 0, 0))
            # 获取ROI区域统计
            stats = img.get_statistics(roi=roi, hist_bins=8)
            lmean = stats.l_mean()
            print(lmean)
            # 判断棋子类型
            if lmean < 50:
                board[i][j] = 1  # 黑棋
                img.draw_rectangle(roi, color=(255, 0, 0))
                img.draw_string(x+15, y+10, "X", color=(255, 0, 0))
            elif lmean > WHITE_THRESH[0] and lmean < WHITE_THRESH[1]:
                board[i][j] = 2  # 白棋
                img.draw_rectangle(roi, color=(0, 255, 0))
                img.draw_string(x+15, y+10, "O", color=(0, 255, 0))
            else:
                board[i][j] = 0  # 空位
                img.draw_rectangle(roi, color=(0, 0, 255))

    return board

# 主循环
rois = None
clock = time.clock()
while True:
    clock.tick()
    img = sensor.snapshot().lens_corr(1.5)
    img.draw_rectangle(BOARD_ROI, color=(0, 0, 255))

    # 静态rois
    # if rois == None:
    #     # 1. 直接检测九个棋格
    #     rois = detect_individual_cells(img, BOARD_ROI)

    # 动态rois
    rois = detect_individual_cells(img, BOARD_ROI)
    if rois:
        # 2. 检测棋子状态
        board = detect_pieces_state(img, rois)
        black_pieces, white_pieces = detect_available_pieces(img)

        # 3. 输出棋盘状态（按1-9编号）
        print("Board State @ FPS:%.1f" % clock.fps())
        print(f"[1:{board[0][0]} 2:{board[0][1]} 3:{board[0][2]}]")
        print(f"[4:{board[1][0]} 5:{board[1][1]} 6:{board[1][2]}]")
        print(f"[7:{board[2][0]} 8:{board[2][1]} 9:{board[2][2]}]")
        print(f"剩余棋子 - 黑:{black_pieces} 白:{white_pieces}")
        print("-----")

    # 4. 按实际需求调整帧率
    time.sleep_ms(50)  # 约20FPS
