import c4d
from c4d import gui

# Константы
PANZOOM_CAM_NAME = "PanZoomCam"
PANZOOM_LOCK_NAME = "PanZoomLock"
PURPLE_COLOR = c4d.Vector(147/255.0, 88/255.0, 178/255.0)  # #9358B2
BLUE_COLOR = c4d.Vector(0.0, 0.5, 1.0)  # синий
REDSHIFT_CAMERA_TYPE = 1057516

def is_camera(obj):
    return obj and obj.GetType() in [c4d.Ocamera, REDSHIFT_CAMERA_TYPE]

def find_sibling_camera(base_cam, target_name):
    """Находит камеру-сестру с заданным именем на том же уровне."""
    parent = base_cam.GetUp()
    if not parent:
        return None

    child = parent.GetDown()
    while child:
        if child != base_cam and child.GetName() == target_name and is_camera(child):
            return child
        child = child.GetNext()
    return None

def main():
    doc = c4d.documents.GetActiveDocument()
    if not doc:
        gui.MessageDialog("Не удалось получить активный документ.")
        return

    bd = doc.GetActiveBaseDraw()
    if not bd:
        gui.MessageDialog("Не удалось получить активный Viewport.")
        return

    current_cam = bd.GetSceneCamera(doc)
    if not is_camera(current_cam):
        gui.MessageDialog("Активная камера не найдена или не поддерживается.")
        return

    doc.StartUndo()

    if current_cam.GetName() == PANZOOM_CAM_NAME:
        # Переключаемся на PanZoomLock
        target_cam = find_sibling_camera(current_cam, PANZOOM_LOCK_NAME)
        if target_cam:
            bd.SetSceneCamera(target_cam)
            bd[c4d.BASEDRAW_DATA_TINTBORDER_COLOR] = BLUE_COLOR
            print(f"Переключено на {PANZOOM_LOCK_NAME}")
        else:
            gui.MessageDialog(f"{PANZOOM_LOCK_NAME} не найдена рядом с {PANZOOM_CAM_NAME}")
            doc.EndUndo()
            return

    elif current_cam.GetName() == PANZOOM_LOCK_NAME:
        # Переключаемся обратно на PanZoomCam
        target_cam = find_sibling_camera(current_cam, PANZOOM_CAM_NAME)
        if target_cam:
            bd.SetSceneCamera(target_cam)
            bd[c4d.BASEDRAW_DATA_TINTBORDER_COLOR] = PURPLE_COLOR
            print(f"Переключено на {PANZOOM_CAM_NAME}")
        else:
            gui.MessageDialog(f"{PANZOOM_CAM_NAME} не найдена рядом с {PANZOOM_LOCK_NAME}")
            doc.EndUndo()
            return

    else:
        gui.MessageDialog("Текущая активная камера не является ни PanZoomCam, ни PanZoomLock.")
        doc.EndUndo()
        return

    c4d.EventAdd()
    doc.EndUndo()

if __name__ == "__main__":
    main()
