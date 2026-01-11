import c4d
from c4d import gui

# Константы
PANZOOM_CAM_NAME   = "PanZoomCam"
PANZOOM_LOCK_NAME  = "PanZoomLock"
TWOD_PANZOOM_NAME  = "2DPanZoom"
PURPLE_COLOR       = c4d.Vector(147/255.0, 88/255.0, 178/255.0)
BLUE_COLOR         = c4d.Vector(0.0, 0.5, 1.0)
REDSHIFT_CAMERA_TYPE = 1057516

SPECIAL_NAMES = {PANZOOM_CAM_NAME, PANZOOM_LOCK_NAME}

def is_camera(obj):
    return obj and obj.GetType() in [c4d.Ocamera, REDSHIFT_CAMERA_TYPE]

def get_true_parent_camera(obj):
    """Поднимаемся вверх до первой камеры, которая НЕ PanZoomCam/PanZoomLock"""
    current = obj
    while current:
        if is_camera(current) and current.GetName() not in SPECIAL_NAMES:
            return current
        current = current.GetUp()
    return None

def find_panzoom_pair(current_obj):
    parent = get_true_parent_camera(current_obj)
    if not parent:
        print("→ Настоящая родительская камера (не PanZoom*) не найдена")
        return None, None

    print(f"→ Настоящая родительская камера: {parent.GetName()}")

    # Ищем 2DPanZoom под ней
    twod = None
    child = parent.GetDown()
    while child:
        if child.GetName() == TWOD_PANZOOM_NAME:
            twod = child
            print(f"→ Найден {TWOD_PANZOOM_NAME}")
            break
        child = child.GetNext()

    panzoom_cam = None
    if twod:
        cam = twod.GetDown()
        if cam and cam.GetName() == PANZOOM_CAM_NAME and is_camera(cam):
            panzoom_cam = cam
            print("→ PanZoomCam найден внутри 2DPanZoom")
        else:
            print("→ PanZoomCam НЕ найден внутри 2DPanZoom")

    # PanZoomLock под родительской
    panzoom_lock = None
    child = parent.GetDown()
    while child:
        if child.GetName() == PANZOOM_LOCK_NAME and is_camera(child):
            panzoom_lock = child
            print("→ PanZoomLock найден")
            break
        child = child.GetNext()

    if not panzoom_lock:
        print("→ PanZoomLock НЕ найден")

    return panzoom_cam, panzoom_lock

def main():
    doc = c4d.documents.GetActiveDocument()
    if not doc:
        return gui.MessageDialog("Нет документа")

    bd = doc.GetActiveBaseDraw()
    if not bd:
        return gui.MessageDialog("Нет видового окна")

    current = bd.GetSceneCamera(doc)
    if not is_camera(current):
        return gui.MessageDialog("Текущая — не камера")

    print("\n" + "="*70)
    print("ОТЛАДКА ПЕРЕКЛЮЧАТЕЛЯ")
    print(f"Текущая активная камера: {current.GetName() if current else 'None'}")
    print("="*70 + "\n")

    doc.StartUndo()

    panzoom_cam, panzoom_lock = find_panzoom_pair(current)

    if not panzoom_cam and not panzoom_lock:
        gui.MessageDialog(
            "Не найдены PanZoomCam / PanZoomLock.\n\n"
            "Смотрите консоль — там показано, где именно поиск остановился.\n"
            "Чаще всего проблема в том, что:\n"
            "• Объекты не созданы или переименованы\n"
            "• Вы не внутри нужной иерархии\n"
            "• После undo иерархия сломалась"
        )
        doc.EndUndo()
        return

    # Переключение
    if current.GetName() == PANZOOM_CAM_NAME or current == panzoom_cam:
        if panzoom_lock:
            bd.SetSceneCamera(panzoom_lock)
            bd[c4d.BASEDRAW_DATA_TINTBORDER_COLOR] = BLUE_COLOR
            print("→ УСПЕХ: переключено на PanZoomLock (синий)")
        else:
            gui.MessageDialog("PanZoomLock найден в поиске, но не может быть использован")
    else:
        if panzoom_cam:
            bd.SetSceneCamera(panzoom_cam)
            bd[c4d.BASEDRAW_DATA_TINTBORDER_COLOR] = PURPLE_COLOR
            print("→ УСПЕХ: переключено на PanZoomCam (фиолетовый)")
        else:
            gui.MessageDialog("PanZoomCam найден в поиске, но не может быть использован")

    c4d.EventAdd()
    doc.EndUndo()

if __name__ == "__main__":
    main()