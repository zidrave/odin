import curses
import sys
import os
import time
import termios

def guardar_archivo(lineas, nombre):
    try:
        with open(nombre, 'w') as f:
            for linea in lineas:
                f.write(linea + '\n')
        return True
    except Exception as e:
        return False

def pedir_nombre_archivo(stdscr):
    curses.echo()
    prompt = "filename to save: "
    prompt_x = len(prompt)
    stdscr.addstr(curses.LINES - 1, 0, prompt)
    stdscr.clrtoeol()
    nombre = ''
    pos = 0
    scroll = 0
    
    while True:
        key = stdscr.getch()
        if key in (10, 13):  # Enter
            break
        elif key in (8, 127, curses.KEY_BACKSPACE):  # Backspace
            if pos > 0:
                nombre = nombre[:pos-1] + nombre[pos:]
                pos -= 1
        elif key == curses.KEY_LEFT:
            if pos > 0:
                pos -= 1
        elif key == curses.KEY_RIGHT:
            if pos < len(nombre):
                pos += 1
        elif key == curses.KEY_HOME:
            pos = 0
        elif key == curses.KEY_END:
            pos = len(nombre)
        elif 32 <= key <= 126:  # Printable characters
            nombre = nombre[:pos] + chr(key) + nombre[pos:]
            pos += 1

        # Corregido: Manejo del scroll horizontal
        maxw = curses.COLS - prompt_x - 1
        if maxw <= 0:
            maxw = 1
            
        # Ajustar scroll para mantener el cursor visible
        if pos < scroll:
            scroll = pos
        elif pos >= scroll + maxw:  # Cambio aquí: >= en lugar de >
            scroll = pos - maxw + 1
        
        # Asegurar que scroll no sea negativo
        scroll = max(0, scroll)
        
        # Mostrar la parte visible del nombre
        visible = nombre[scroll:scroll + maxw]
        stdscr.addstr(curses.LINES - 1, prompt_x, ' ' * maxw)  # Limpiar línea
        if visible:
            stdscr.addstr(curses.LINES - 1, prompt_x, visible)
        
        # Posicionar cursor - Corregido el cálculo
        cursor_pos = pos - scroll
        # Asegurar que el cursor esté en el rango visible
        if cursor_pos >= maxw:
            cursor_pos = maxw - 1
        elif cursor_pos < 0:
            cursor_pos = 0
            
        stdscr.move(curses.LINES - 1, prompt_x + cursor_pos)

    curses.noecho()
    return nombre

def editor(stdscr, archivo_inicial=None):
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_CYAN, -1)
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(5, curses.COLOR_RED, -1)
    curses.init_pair(6, curses.COLOR_BLUE, -1)

    curses.curs_set(1)
    stdscr.keypad(True)

    archivo = archivo_inicial
    lineas = ['']
    modo_comando = False
    comando = ''
    cursor_x, cursor_y = 0, 0
    offset_y = 0
    scroll_x = 0
    mostrar_lineas = True

    mostrar_mensaje = ''
    mostrar_mensaje_color = 0
    mostrar_mensaje_tiempo = 0

    seleccionando = False
    sel_inicio = None
    sel_fin = None
    portapapeles = ''

    # Cargar archivo si existe
    if archivo and os.path.exists(archivo):
        try:
            with open(archivo, 'r') as f:
                contenido = f.read()
                if contenido:
                    lineas = contenido.splitlines()
                    if not lineas:  # Archivo vacío
                        lineas = ['']
                else:
                    lineas = ['']
        except Exception as e:
            lineas = ['']
            mostrar_mensaje = f"Error al cargar archivo: {str(e)}"
            mostrar_mensaje_color = curses.color_pair(5)
            mostrar_mensaje_tiempo = time.time()

    def mostrar_mensaje_func(msg, color=curses.color_pair(6)):
        nonlocal mostrar_mensaje, mostrar_mensaje_color, mostrar_mensaje_tiempo
        mostrar_mensaje = msg
        mostrar_mensaje_color = color
        mostrar_mensaje_tiempo = time.time()

    def validar_cursor():
        nonlocal cursor_x, cursor_y
        # Validar bounds de cursor_y
        cursor_y = max(0, min(cursor_y, len(lineas) - 1))
        # Validar bounds de cursor_x
        if cursor_y < len(lineas):
            cursor_x = max(0, min(cursor_x, len(lineas[cursor_y])))

    while True:
        validar_cursor()
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        # Título
        titulo = archivo if archivo else "[Sin nombre]"
        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(0, 0, " " * (w - 1))
        stdscr.attroff(curses.color_pair(1))
        stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        titulo_pos = max(0, (w - len(titulo)) // 2)
        stdscr.addstr(0, titulo_pos, titulo[:w-1])
        stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)

        # Mostrar contenido
        for idx in range(offset_y, min(offset_y + h - 2, len(lineas))):
            linea = lineas[idx]
            line_start_x = 0
            
            # Números de línea
            if mostrar_lineas:
                stdscr.attron(curses.color_pair(2))
                stdscr.addstr(idx - offset_y + 1, 0, f"{idx + 1:>3} ")
                stdscr.attroff(curses.color_pair(2))
                line_start_x = 4

            # Calcular texto visible
            max_line_width = w - line_start_x - 1
            if max_line_width <= 0:
                continue
                
            visible_line = linea[scroll_x:scroll_x + max_line_width]

            # Manejo de selección
            if seleccionando and sel_inicio and sel_fin:
                sy, sx = sel_inicio
                ey, ex = sel_fin
                if (sy, sx) > (ey, ex):
                    sy, sx, ey, ex = ey, ex, sy, sx
                    
                if sy <= idx <= ey:
                    inicio = 0
                    fin = len(visible_line)
                    if idx == sy:
                        inicio = max(0, sx - scroll_x)
                    if idx == ey:
                        fin = min(len(visible_line), ex - scroll_x)
                    
                    # Mostrar texto normal antes de selección
                    if inicio > 0:
                        stdscr.addstr(idx - offset_y + 1, line_start_x, visible_line[:inicio])
                    
                    # Mostrar texto seleccionado
                    if fin > inicio:
                        stdscr.attron(curses.A_REVERSE)
                        stdscr.addstr(idx - offset_y + 1, line_start_x + inicio, visible_line[inicio:fin])
                        stdscr.attroff(curses.A_REVERSE)
                    
                    # Mostrar texto normal después de selección
                    if fin < len(visible_line):
                        stdscr.addstr(idx - offset_y + 1, line_start_x + fin, visible_line[fin:])
                else:
                    stdscr.addstr(idx - offset_y + 1, line_start_x, visible_line)
            else:
                stdscr.addstr(idx - offset_y + 1, line_start_x, visible_line)

        # Ajustar scroll horizontal
        line_start_x = 4 if mostrar_lineas else 0
        max_display_width = w - line_start_x - 1
        
        if cursor_x < scroll_x:
            scroll_x = cursor_x
        elif cursor_x >= scroll_x + max_display_width:
            scroll_x = cursor_x - max_display_width + 1
        
        scroll_x = max(0, scroll_x)

        # Ajustar scroll vertical
        if cursor_y < offset_y:
            offset_y = cursor_y
        elif cursor_y >= offset_y + h - 2:
            offset_y = cursor_y - (h - 3)
        
        offset_y = max(0, offset_y)

        # Barra de estado
        if mostrar_mensaje and time.time() - mostrar_mensaje_tiempo < 2.0:
            stdscr.attron(mostrar_mensaje_color)
            stdscr.addstr(h - 1, 0, mostrar_mensaje[:w - 1])
            stdscr.clrtoeol()
            stdscr.attroff(mostrar_mensaje_color)
        elif modo_comando:
            stdscr.attron(curses.color_pair(3))
            stdscr.addstr(h - 1, 0, f":{comando}"[:w - 1])
            stdscr.clrtoeol()
            stdscr.attroff(curses.color_pair(3))
        else:
            # Mostrar posición del cursor
            info = f"Línea: {cursor_y + 1}, Col: {cursor_x + 1}"
            stdscr.addstr(h - 1, 0, info[:w - 1])
            stdscr.clrtoeol()

        # Posicionar cursor
        if not modo_comando and offset_y <= cursor_y < offset_y + h - 2:
            cursor_offset = line_start_x
            display_x = cursor_x - scroll_x
            if 0 <= display_x < max_display_width:
                stdscr.move(cursor_y - offset_y + 1, display_x + cursor_offset)

        stdscr.refresh()
        key = stdscr.getch()

        # Actualizar fin de selección
        if seleccionando:
            sel_fin = (cursor_y, cursor_x)

        # Manejar tecla ESC y combinaciones
        if key == 27:
            stdscr.nodelay(True)
            siguiente = stdscr.getch()
            stdscr.nodelay(False)
            if siguiente == -1 or siguiente == ord('e'):
                modo_comando = not modo_comando
                comando = ''
                seleccionando = False
                continue
            elif siguiente == ord('m'):
                if not seleccionando:
                    sel_inicio = (cursor_y, cursor_x)
                    sel_fin = (cursor_y, cursor_x)
                    seleccionando = True
                    mostrar_mensaje_func("Modo selección activado")
                else:
                    seleccionando = False
                    mostrar_mensaje_func("Selección cancelada")
                continue
            elif siguiente == ord('s'):
                if not archivo:
                    archivo = pedir_nombre_archivo(stdscr)
                if archivo:
                    if guardar_archivo(lineas, archivo):
                        mostrar_mensaje_func(f"Archivo guardado: {archivo}")
                    else:
                        mostrar_mensaje_func("Error al guardar archivo", curses.color_pair(5))
                continue
            elif siguiente == ord('q'):
                break
            elif siguiente == ord('c'):
                if seleccionando and sel_inicio and sel_fin:
                    sy, sx = sel_inicio
                    ey, ex = sel_fin
                    if (sy, sx) > (ey, ex):
                        sy, sx, ey, ex = ey, ex, sy, sx
                    
                    if sy == ey:
                        portapapeles = lineas[sy][sx:ex]
                    else:
                        texto_copiado = []
                        texto_copiado.append(lineas[sy][sx:])
                        for i in range(sy + 1, ey):
                            texto_copiado.append(lineas[i])
                        texto_copiado.append(lineas[ey][:ex])
                        portapapeles = '\n'.join(texto_copiado)
                    
                    mostrar_mensaje_func("Texto copiado")
                continue
            elif siguiente == ord('x'):
                if seleccionando and sel_inicio and sel_fin:
                    sy, sx = sel_inicio
                    ey, ex = sel_fin
                    if (sy, sx) > (ey, ex):
                        sy, sx, ey, ex = ey, ex, sy, sx
                    
                    if sy == ey:
                        portapapeles = lineas[sy][sx:ex]
                        lineas[sy] = lineas[sy][:sx] + lineas[sy][ex:]
                        cursor_x = sx
                    else:
                        texto_cortado = []
                        texto_cortado.append(lineas[sy][sx:])
                        for i in range(sy + 1, ey):
                            texto_cortado.append(lineas[i])
                        texto_cortado.append(lineas[ey][:ex])
                        portapapeles = '\n'.join(texto_cortado)
                        
                        lineas[sy] = lineas[sy][:sx] + lineas[ey][ex:]
                        del lineas[sy + 1:ey + 1]
                        cursor_y = sy
                        cursor_x = sx
                    
                    seleccionando = False
                    mostrar_mensaje_func("Texto cortado")
                continue
            elif siguiente == ord('v'):
                if portapapeles:
                    partes = portapapeles.split('\n')
                    if len(partes) == 1:
                        # Pegar en una línea
                        lineas[cursor_y] = lineas[cursor_y][:cursor_x] + partes[0] + lineas[cursor_y][cursor_x:]
                        cursor_x += len(partes[0])
                    else:
                        # Pegar multilínea
                        inicio = lineas[cursor_y][:cursor_x] + partes[0]
                        fin = partes[-1] + lineas[cursor_y][cursor_x:]
                        lineas[cursor_y] = inicio
                        
                        for i in range(1, len(partes) - 1):
                            lineas.insert(cursor_y + i, partes[i])
                        lineas.insert(cursor_y + len(partes) - 1, fin)
                        
                        cursor_y += len(partes) - 1
                        cursor_x = len(partes[-1])
                    
                    mostrar_mensaje_func("Texto pegado")
                continue

        # Modo comando
        if modo_comando:
            if key in (10, 13):  # Enter
                comando_input = comando.strip()
                if comando_input == 'q':
                    break
                elif comando_input == 'l':
                    mostrar_lineas = not mostrar_lineas
                    mostrar_mensaje_func(f"Números de línea: {'ON' if mostrar_lineas else 'OFF'}")
                elif comando_input == 'w':
                    if not archivo:
                        archivo = pedir_nombre_archivo(stdscr)
                    if archivo:
                        if guardar_archivo(lineas, archivo):
                            mostrar_mensaje_func(f"Archivo guardado: {archivo}")
                        else:
                            mostrar_mensaje_func("Error al guardar archivo", curses.color_pair(5))
                elif comando_input == 'wq':
                    if not archivo:
                        archivo = pedir_nombre_archivo(stdscr)
                    if archivo:
                        if guardar_archivo(lineas, archivo):
                            break
                        else:
                            mostrar_mensaje_func("Error al guardar archivo", curses.color_pair(5))
                elif comando_input.startswith('wf:'):
                    nuevo_nombre = comando_input[3:].strip()
                    if nuevo_nombre:
                        if guardar_archivo(lineas, nuevo_nombre):
                            mostrar_mensaje_func(f"Copia guardada como: {nuevo_nombre}")
                        else:
                            mostrar_mensaje_func("Error al guardar copia", curses.color_pair(5))
                
                comando = ''
                modo_comando = False
            elif key in (8, 127, curses.KEY_BACKSPACE):
                if comando:
                    comando = comando[:-1]
            elif 32 <= key <= 126:
                comando += chr(key)
        
        # Modo edición
        else:
            if key == curses.KEY_UP:
                if cursor_y > 0:
                    cursor_y -= 1
                    cursor_x = min(cursor_x, len(lineas[cursor_y]))
            elif key == curses.KEY_DOWN:
                if cursor_y < len(lineas) - 1:
                    cursor_y += 1
                    cursor_x = min(cursor_x, len(lineas[cursor_y]))
            elif key == curses.KEY_LEFT:
                if cursor_x > 0:
                    cursor_x -= 1
                elif cursor_y > 0:  # Ir al final de la línea anterior
                    cursor_y -= 1
                    cursor_x = len(lineas[cursor_y])
            elif key == curses.KEY_RIGHT:
                if cursor_x < len(lineas[cursor_y]):
                    cursor_x += 1
                elif cursor_y < len(lineas) - 1:  # Ir al inicio de la siguiente línea
                    cursor_y += 1
                    cursor_x = 0
            elif key == curses.KEY_HOME:
                cursor_x = 0
            elif key == curses.KEY_END:
                cursor_x = len(lineas[cursor_y])
            elif key == curses.KEY_NPAGE:  # Page Down
                cursor_y = min(len(lineas) - 1, cursor_y + (h - 2))
                cursor_x = min(cursor_x, len(lineas[cursor_y]))
            elif key == curses.KEY_PPAGE:  # Page Up
                cursor_y = max(0, cursor_y - (h - 2))
                cursor_x = min(cursor_x, len(lineas[cursor_y]))
            elif key == 10:  # Enter
                nueva = lineas[cursor_y][cursor_x:]
                lineas[cursor_y] = lineas[cursor_y][:cursor_x]
                lineas.insert(cursor_y + 1, nueva)
                cursor_y += 1
                cursor_x = 0
            elif key in (127, curses.KEY_BACKSPACE):
                if cursor_x > 0:
                    lineas[cursor_y] = lineas[cursor_y][:cursor_x - 1] + lineas[cursor_y][cursor_x:]
                    cursor_x -= 1
                elif cursor_y > 0:  # Unir con línea anterior
                    prev_len = len(lineas[cursor_y - 1])
                    lineas[cursor_y - 1] += lineas[cursor_y]
                    del lineas[cursor_y]
                    cursor_y -= 1
                    cursor_x = prev_len
            elif key == curses.KEY_DC:  # Delete
                if cursor_x < len(lineas[cursor_y]):
                    lineas[cursor_y] = lineas[cursor_y][:cursor_x] + lineas[cursor_y][cursor_x + 1:]
                elif cursor_y < len(lineas) - 1:  # Unir con línea siguiente
                    lineas[cursor_y] += lineas[cursor_y + 1]
                    del lineas[cursor_y + 1]
            elif 32 <= key <= 126:  # Caracteres imprimibles
                lineas[cursor_y] = lineas[cursor_y][:cursor_x] + chr(key) + lineas[cursor_y][cursor_x:]
                cursor_x += 1

        # Asegurar que siempre haya al menos una línea
        if not lineas:
            lineas = ['']
            cursor_y = 0
            cursor_x = 0

def main():
    # Configurar terminal
    os.environ.setdefault('ESCDELAY', '25')
    
    try:
        fd = sys.stdin.fileno()
        attrs = termios.tcgetattr(fd)
        attrs[3] = attrs[3] & ~termios.IXON
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
    except:
        pass  # Ignorar errores de configuración de terminal

    archivo = sys.argv[1] if len(sys.argv) > 1 else None
    curses.wrapper(editor, archivo)

if __name__ == "__main__":
    main()
