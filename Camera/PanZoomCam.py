import c4d
from c4d import gui

# Константы
RESET_TRANSFORM_CMD_ID = 1019940
PANZOOM_CAM_NAME = "PanZoomCam"
PANZOOM_LOCK_NAME = "PanZoomLock"
PURPLE_COLOR = c4d.Vector(147/255.0, 88/255.0, 178/255.0)  # #9358B2
DEFAULT_COLOR = c4d.Vector(0.0, 0.0, 0.0)  # #000000
REDSHIFT_CAMERA_TYPE = 1057516  # Тип Redshift-камеры
RECTANGLE_SELECTION_CMD_ID = 200000084  # ID команды для Rectangle Selection (обновлено)

def find_child_panzoom(cam, name):
    """Ищет дочернюю камеру с указанным именем."""
    child = cam.GetDown()
    while child:
        if child.GetName() == name:
            return child
        child = child.GetNext()
    return None

def remove_animation_tracks(obj, doc):
    """Удаляет анимационные треки для позиции, вращения и масштабирования."""
    track_ids = [
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION), c4d.DescLevel(c4d.VECTOR_X)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION), c4d.DescLevel(c4d.VECTOR_Y)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION), c4d.DescLevel(c4d.VECTOR_Z)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_ROTATION), c4d.DescLevel(c4d.VECTOR_X)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_ROTATION), c4d.DescLevel(c4d.VECTOR_Y)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_ROTATION), c4d.DescLevel(c4d.VECTOR_Z)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_SCALE), c4d.DescLevel(c4d.VECTOR_X)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_SCALE), c4d.DescLevel(c4d.VECTOR_Y)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_SCALE), c4d.DescLevel(c4d.VECTOR_Z))
    ]
    
    tracks = obj.GetCTracks()
    for track in tracks[:]:
        if track.GetDescriptionID() in track_ids:
            doc.AddUndo(c4d.UNDOTYPE_DELETE, track)
            track.Remove()

def main():
    # Получаем активный документ
    doc = c4d.documents.GetActiveDocument()
    if not doc:
        gui.MessageDialog("Не удалось получить активный документ.")
        return
    
    doc.StartUndo()
    
    # Получаем активный BaseDraw
    bd = doc.GetActiveBaseDraw()
    if not bd:
        gui.MessageDialog("Не удалось получить активный Viewport.")
        doc.EndUndo()
        return
    
    # Получаем текущую камеру в видовом окне (активная камера)
    active_cam = bd.GetSceneCamera(doc)
    if not active_cam:
        active_cam = doc.SearchObjectType(c4d.Ocamera)
        if not active_cam:
            gui.MessageDialog("В сцене нет камеры!")
            doc.EndUndo()
            return
    
    # Определяем, является ли активная камера Redshift-камерой
    is_redshift = active_cam.GetType() == REDSHIFT_CAMERA_TYPE
    
    # Проверяем наличие PanZoomCam или PanZoomLock (активных или дочерних)
    is_panzoom_active = active_cam.GetName() == PANZOOM_CAM_NAME
    is_panzoom_lock_active = active_cam.GetName() == PANZOOM_LOCK_NAME
    
    # Повторный запуск
    if is_panzoom_active or is_panzoom_lock_active or find_child_panzoom(active_cam, PANZOOM_CAM_NAME) or find_child_panzoom(active_cam, PANZOOM_LOCK_NAME):
        parent_cam = active_cam if not (is_panzoom_active or is_panzoom_lock_active) else active_cam.GetUp()
        if not parent_cam:
            gui.MessageDialog("Не удалось найти родительскую камеру!")
            doc.EndUndo()
            return
        
        # 1. Переключаемся на родительскую камеру
        bd.SetSceneCamera(parent_cam)
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, bd)
        
        # Принудительно обновляем сцену
        c4d.EventAdd()
        
        # 2. Присваиваем чёрный цвет BASEDRAW_DATA_TINTBORDER_COLOR
        bd[c4d.BASEDRAW_DATA_TINTBORDER_COLOR] = DEFAULT_COLOR
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, bd)
        
        # Повторно ищем дочерние камеры после переключения
        existing_panzoom = find_child_panzoom(parent_cam, PANZOOM_CAM_NAME)
        existing_panzoom_lock = find_child_panzoom(parent_cam, PANZOOM_LOCK_NAME)
        
        # 3. Удаляем PanZoomCam и PanZoomLock, если они существуют
        if existing_panzoom:
            doc.AddUndo(c4d.UNDOTYPE_DELETE, existing_panzoom)
            existing_panzoom.Remove()
        if existing_panzoom_lock:
            doc.AddUndo(c4d.UNDOTYPE_DELETE, existing_panzoom_lock)
            existing_panzoom_lock.Remove()
        
        # Устанавливаем Viewport Visibility родителя на Default
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, parent_cam)
        parent_cam[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = c4d.OBJECT_UNDEF  # Default
        
        # 4. Переключаем инструмент на Rectangle Selection
        c4d.CallCommand(RECTANGLE_SELECTION_CMD_ID)
        c4d.EventAdd()  # Принудительное обновление после переключения инструмента
        
        print("Переключено на родительскую камеру, цвет сброшен, 'PanZoomCam' и 'PanZoomLock' удалены, видимость восстановлена, инструмент переключён на Rectangle Selection.")
        doc.EndUndo()
        c4d.EventAdd()
        return
    
    # Первый запуск
    
    # Дублируем активную камеру 2 раза
    panzoom_cam = active_cam.GetClone()
    if not panzoom_cam:
        gui.MessageDialog("Не удалось дублировать камеру для PanZoomCam!")
        doc.EndUndo()
        return
    
    panzoom_lock = active_cam.GetClone()
    if not panzoom_lock:
        gui.MessageDialog("Не удалось дублировать камеру для PanZoomLock!")
        doc.EndUndo()
        return
    
    # Переименовываем первый дубликат в "PanZoomCam"
    panzoom_cam.SetName(PANZOOM_CAM_NAME)
    
    # Переименовываем второй дубликат в "PanZoomLock"
    panzoom_lock.SetName(PANZOOM_LOCK_NAME)
    
    # Удаляем анимационные треки у дубликатов
    remove_animation_tracks(panzoom_cam, doc)
    remove_animation_tracks(panzoom_lock, doc)
    
    # Удаляем все теги на дубликатах
    for tag in panzoom_cam.GetTags()[:]:
        doc.AddUndo(c4d.UNDOTYPE_DELETE, tag)
        tag.Remove()
    for tag in panzoom_lock.GetTags()[:]:
        doc.AddUndo(c4d.UNDOTYPE_DELETE, tag)
        tag.Remove()
    
    # Помещаем дубликаты как дочерние объекты активной камеры
    doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, panzoom_cam)
    panzoom_cam.InsertUnder(active_cam)
    doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, panzoom_lock)
    panzoom_lock.InsertUnder(active_cam)
    
    # Выполняем "Reset Transform" на "PanZoomCam" и "PanZoomLock"
    doc.SetActiveObject(panzoom_cam)
    c4d.CallCommand(RESET_TRANSFORM_CMD_ID)
    doc.SetActiveObject(panzoom_lock)
    c4d.CallCommand(RESET_TRANSFORM_CMD_ID)
    
    # Добавляем Protection Tag на "PanZoomCam" и "PanZoomLock"
    protection_tag_cam = c4d.BaseTag(c4d.Tprotection)
    doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, protection_tag_cam)
    panzoom_cam.InsertTag(protection_tag_cam)
    protection_tag_lock = c4d.BaseTag(c4d.Tprotection)
    doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, protection_tag_lock)
    panzoom_lock.InsertTag(protection_tag_lock)
    
    # Устанавливаем Display Color "PanZoomCam" на фиолетовый (#9358B2)
    doc.AddUndo(c4d.UNDOTYPE_CHANGE, panzoom_cam)
    panzoom_cam[c4d.ID_BASEOBJECT_COLOR] = PURPLE_COLOR
    
    # Присваиваем этот цвет BASEDRAW_DATA_TINTBORDER_COLOR
    doc.AddUndo(c4d.UNDOTYPE_CHANGE, bd)
    bd[c4d.BASEDRAW_DATA_TINTBORDER_COLOR] = PURPLE_COLOR
    
    # Устанавливаем Viewport Visibility на "Off" для активной камеры и дубликатов
    doc.AddUndo(c4d.UNDOTYPE_CHANGE, active_cam)
    active_cam[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = c4d.OBJECT_OFF
    doc.AddUndo(c4d.UNDOTYPE_CHANGE, panzoom_cam)
    panzoom_cam[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = c4d.OBJECT_OFF
    doc.AddUndo(c4d.UNDOTYPE_CHANGE, panzoom_lock)
    panzoom_lock[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = c4d.OBJECT_OFF
    
    # Привязываем Shift и Focal Length "PanZoomLock" к активной камере через XPresso
    xpresso_tag = c4d.BaseTag(c4d.Texpresso)
    doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, xpresso_tag)
    panzoom_lock.InsertTag(xpresso_tag)
    nodemaster = xpresso_tag.GetNodeMaster()
    
    # Узел для PanZoomLock
    lock_node = nodemaster.CreateNode(nodemaster.GetRoot(), c4d.ID_OPERATOR_OBJECT, None, x=50, y=50)
    lock_node[c4d.GV_OBJECT_OBJECT_ID] = panzoom_lock
    
    # Узел для активной камеры
    parent_node = nodemaster.CreateNode(nodemaster.GetRoot(), c4d.ID_OPERATOR_OBJECT, None, x=200, y=50)
    parent_node[c4d.GV_OBJECT_OBJECT_ID] = active_cam
    
    # Связываем параметры
    if is_redshift:
        shift_out = parent_node.AddPort(c4d.GV_PORT_OUTPUT, c4d.RSCAMERAOBJECT_SENSOR_SHIFT)
        shift_in = lock_node.AddPort(c4d.GV_PORT_INPUT, c4d.RSCAMERAOBJECT_SENSOR_SHIFT)
        if shift_out and shift_in:
            shift_out.Connect(shift_in)
        else:
            print("Не удалось связать RSCAMERAOBJECT_SENSOR_SHIFT")
    else:
        shift_x_out = parent_node.AddPort(c4d.GV_PORT_OUTPUT, c4d.CAMERAOBJECT_FILM_OFFSET_X)
        shift_x_in = lock_node.AddPort(c4d.GV_PORT_INPUT, c4d.CAMERAOBJECT_FILM_OFFSET_X)
        if shift_x_out and shift_x_in:
            shift_x_out.Connect(shift_x_in)
        
        shift_y_out = parent_node.AddPort(c4d.GV_PORT_OUTPUT, c4d.CAMERAOBJECT_FILM_OFFSET_Y)
        shift_y_in = lock_node.AddPort(c4d.GV_PORT_INPUT, c4d.CAMERAOBJECT_FILM_OFFSET_Y)
        if shift_y_out and shift_y_in:
            shift_y_out.Connect(shift_y_in)
    
    # Связываем Focal Length (общий для обеих)
    focal_out = parent_node.AddPort(c4d.GV_PORT_OUTPUT, c4d.CAMERA_FOCUS)
    focal_in = lock_node.AddPort(c4d.GV_PORT_INPUT, c4d.CAMERA_FOCUS)
    if focal_out and focal_in:
        focal_out.Connect(focal_in)
    
    # Делаем "PanZoomCam" активной камерой (в самом конце)
    c4d.EventAdd()  # Принудительное обновление перед переключением
    bd.SetSceneCamera(panzoom_cam)
    doc.AddUndo(c4d.UNDOTYPE_CHANGE, bd)
    
    print("Камеры дублированы как 'PanZoomCam' и 'PanZoomLock', анимация удалена, теги удалены, трансформация сброшена, цвет установлен, видимость отключена, активная камера - PanZoomCam.")
    
    doc.EndUndo()
    c4d.EventAdd()

if __name__ == "__main__":
    main()