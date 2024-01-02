async def get_y_m_d_text(dmy: dict) -> str:
    words = {'y': ['лет', 'год', 'года'], 'm': ['месяцев', 'месяц', 'месяца'], 'd': ['дней', 'день', 'дня']}

    out = []
    for k, v in dmy.items():
        remainder = v % 10
        if v == 0 or remainder == 0 or remainder >= 5 or v in range(11, 19):
            st = str(v), words[k][0]
        elif remainder == 1:
            st = str(v), words[k][1]
        else:
            st = str(v), words[k][2]
        out.append(" ".join(st))
    return " ".join(out)