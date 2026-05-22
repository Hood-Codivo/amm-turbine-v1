from __future__ import annotations

from pathlib import Path
import math
import textwrap


OUT = Path(__file__).resolve().parents[1] / "docs" / "amm-flow-diagram.pdf"
PAGE_W, PAGE_H = 842, 595  # A4 landscape in points


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class Pdf:
    def __init__(self) -> None:
        self.pages: list[str] = []

    def add_page(self, content: str) -> None:
        self.pages.append(content)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        objects: list[bytes] = []

        def add(obj: str | bytes) -> int:
            if isinstance(obj, str):
                obj = obj.encode("latin-1")
            objects.append(obj)
            return len(objects)

        catalog_id = add("<< /Type /Catalog /Pages 2 0 R >>")
        pages_placeholder_id = add(b"")
        font_regular_id = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        font_bold_id = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        font_mono_id = add("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

        page_ids: list[int] = []
        for content in self.pages:
            stream = content.encode("latin-1")
            content_id = add(
                b"<< /Length "
                + str(len(stream)).encode("ascii")
                + b" >>\nstream\n"
                + stream
                + b"\nendstream"
            )
            page_id = add(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R /F3 {font_mono_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            )
            page_ids.append(page_id)

        kids = " ".join(f"{pid} 0 R" for pid in page_ids)
        objects[pages_placeholder_id - 1] = (
            f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("latin-1")
        )

        offsets = [0]
        body = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        for i, obj in enumerate(objects, start=1):
            offsets.append(len(body))
            body.extend(f"{i} 0 obj\n".encode("ascii"))
            body.extend(obj)
            body.extend(b"\nendobj\n")

        xref_at = len(body)
        body.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        body.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            body.extend(f"{off:010d} 00000 n \n".encode("ascii"))
        body.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode(
                "ascii"
            )
        )
        path.write_bytes(body)


class Canvas:
    def __init__(self) -> None:
        self.ops: list[str] = []

    def rgb(self, r: int, g: int, b: int, stroke: bool = False) -> None:
        op = "RG" if stroke else "rg"
        self.ops.append(f"{r/255:.3f} {g/255:.3f} {b/255:.3f} {op}")

    def line_width(self, width: float) -> None:
        self.ops.append(f"{width:.2f} w")

    def rect(self, x: float, y: float, w: float, h: float, fill=(255, 255, 255), stroke=(35, 48, 68), lw=1.0) -> None:
        self.rgb(*fill)
        self.ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")
        self.rgb(*stroke, stroke=True)
        self.line_width(lw)
        self.ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re S")

    def line(self, x1: float, y1: float, x2: float, y2: float, color=(35, 48, 68), lw=1.2) -> None:
        self.rgb(*color, stroke=True)
        self.line_width(lw)
        self.ops.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def arrow(self, x1: float, y1: float, x2: float, y2: float, color=(35, 48, 68), lw=1.4) -> None:
        self.line(x1, y1, x2, y2, color, lw)
        ang = math.atan2(y2 - y1, x2 - x1)
        size = 8
        a1 = ang + math.pi * 0.82
        a2 = ang - math.pi * 0.82
        p1 = (x2 + size * math.cos(a1), y2 + size * math.sin(a1))
        p2 = (x2 + size * math.cos(a2), y2 + size * math.sin(a2))
        self.rgb(*color)
        self.ops.append(
            f"{x2:.2f} {y2:.2f} m {p1[0]:.2f} {p1[1]:.2f} l {p2[0]:.2f} {p2[1]:.2f} l f"
        )

    def text(self, x: float, y: float, s: str, size=10, font="F1", color=(35, 48, 68)) -> None:
        self.rgb(*color)
        self.ops.append(f"BT /{font} {size:.1f} Tf {x:.2f} {y:.2f} Td ({esc(s)}) Tj ET")

    def wrap(self, x: float, y: float, s: str, width: int, size=10, leading=13, font="F1", color=(35, 48, 68)) -> float:
        lines: list[str] = []
        for para in s.split("\n"):
            lines.extend(textwrap.wrap(para, width=width) or [""])
        for line in lines:
            self.text(x, y, line, size=size, font=font, color=color)
            y -= leading
        return y

    def box(self, x, y, w, h, title, body, fill=(244, 247, 251), accent=(36, 92, 160), title_size=11, body_size=8.5):
        self.rect(x, y, w, h, fill=fill, stroke=accent, lw=1.2)
        self.text(x + 10, y + h - 18, title, size=title_size, font="F2", color=accent)
        self.wrap(x + 10, y + h - 35, body, width=max(18, int(w / (body_size * 0.52))), size=body_size, leading=11)

    def header(self, title: str, subtitle: str = "") -> None:
        self.rgb(28, 39, 55)
        self.ops.append(f"0 {PAGE_H - 70} {PAGE_W} 70 re f")
        self.text(36, PAGE_H - 34, title, size=22, font="F2", color=(255, 255, 255))
        if subtitle:
            self.text(38, PAGE_H - 55, subtitle, size=10, color=(210, 222, 238))

    def footer(self, page: int) -> None:
        self.line(36, 34, PAGE_W - 36, 34, color=(205, 213, 224), lw=0.7)
        self.text(36, 18, "AMM Turbine v1 - flow reference", size=8, color=(95, 105, 120))
        self.text(PAGE_W - 76, 18, f"Page {page}", size=8, color=(95, 105, 120))

    def content(self) -> str:
        return "\n".join(self.ops)


def table(c: Canvas, x: float, y: float, widths: list[float], rows: list[list[str]], header=True, row_h=36):
    h = row_h * len(rows)
    c.rect(x, y - h, sum(widths), h, fill=(255, 255, 255), stroke=(172, 184, 198), lw=0.8)
    cy = y
    for r, row in enumerate(rows):
        fill = (230, 237, 247) if r == 0 and header else (255, 255, 255)
        c.rgb(*fill)
        c.ops.append(f"{x:.2f} {cy-row_h:.2f} {sum(widths):.2f} {row_h:.2f} re f")
        cx = x
        for i, cell in enumerate(row):
            c.rect(cx, cy - row_h, widths[i], row_h, fill=fill, stroke=(210, 218, 228), lw=0.5)
            font = "F2" if r == 0 and header else "F1"
            size = 8.5 if r == 0 and header else 7.8
            c.wrap(cx + 6, cy - 13, cell, width=max(10, int(widths[i] / 4.2)), size=size, leading=9, font=font)
            cx += widths[i]
        cy -= row_h


def page_1(pdf: Pdf) -> None:
    c = Canvas()
    c.header("AMM Turbine v1 Flow Diagram", "What an AMM is, how liquidity becomes LP tokens, and how withdraw/swap flows work")
    c.box(36, 438, 236, 78, "What is an AMM?", "An Automated Market Maker is a pool of two tokens. Traders swap against the pool, and liquidity providers own a share of the pool through LP tokens.", fill=(245, 250, 255), accent=(25, 88, 145), body_size=9)
    c.box(300, 438, 236, 78, "Core idea", "The vaults hold Token A and Token B. The constant-product curve uses x * y = k to price swaps and preserve pool balance.", fill=(248, 249, 244), accent=(78, 115, 34), body_size=9)
    c.box(564, 438, 236, 78, "LP token", "An LP token is a receipt for pool ownership. In the first deposit example: Token A + Token B => 1 LP share unit.", fill=(255, 247, 239), accent=(173, 91, 31), body_size=9)

    c.box(58, 300, 126, 58, "User", "Has Token A and Token B", fill=(245, 247, 251), accent=(45, 55, 72))
    c.arrow(184, 329, 232, 329)
    c.box(232, 286, 152, 86, "Deposit liquidity", "User deposits both assets: token A and token B. Max limits protect against slippage.", fill=(236, 246, 255), accent=(29, 100, 170))
    c.arrow(384, 329, 438, 329)
    c.box(438, 286, 152, 86, "AMM vaults", "vault_x receives Token A. vault_y receives Token B.", fill=(239, 248, 240), accent=(53, 126, 72))
    c.arrow(590, 329, 644, 329)
    c.box(644, 286, 134, 86, "Mint LP", "mint_lp creates LP tokens for the user_lp account.", fill=(255, 244, 232), accent=(187, 96, 37))

    c.box(116, 155, 160, 72, "Withdraw", "User burns LP tokens. Pool sends proportional Token A and Token B back to the user.", fill=(252, 246, 246), accent=(160, 59, 64))
    c.arrow(276, 191, 338, 191)
    c.box(338, 155, 168, 72, "Burn LP", "user_lp decreases; mint_lp supply decreases.", fill=(255, 245, 238), accent=(174, 83, 34))
    c.arrow(506, 191, 568, 191)
    c.box(568, 155, 160, 72, "Return tokens", "vault_x -> user_x and vault_y -> user_y.", fill=(239, 248, 240), accent=(53, 126, 72))

    c.text(44, 105, "Mental model:", size=12, font="F2", color=(28, 39, 55))
    c.wrap(44, 88, "Deposit adds balanced liquidity and mints ownership. Withdraw burns ownership and returns the underlying tokens. Swap trades one token for the other through the pool while the curve updates the effective balances.", width=120, size=9, leading=12)
    c.footer(1)
    pdf.add_page(c.content())


def page_2(pdf: Pdf) -> None:
    c = Canvas()
    c.header("Liquidity Provider Flow", "Initialize, deposit Token A + Token B, then mint LP tokens")
    c.box(36, 450, 148, 62, "1. Initialize pool", "Creates config, LP mint, vault_x, and vault_y.", fill=(245, 250, 255), accent=(25, 88, 145))
    c.arrow(184, 481, 220, 481)
    c.box(220, 450, 148, 62, "2. User prepares", "User owns user_x and user_y token accounts.", fill=(248, 249, 244), accent=(78, 115, 34))
    c.arrow(368, 481, 404, 481)
    c.box(404, 450, 148, 62, "3. Deposit A + B", "AMM computes x and y amounts to transfer.", fill=(236, 246, 255), accent=(29, 100, 170))
    c.arrow(552, 481, 588, 481)
    c.box(588, 450, 148, 62, "4. Mint LP", "AMM signs as config PDA and mints LP to user_lp.", fill=(255, 244, 232), accent=(187, 96, 37))

    c.text(36, 404, "Deposit formula used by the program", size=13, font="F2", color=(28, 39, 55))
    c.box(36, 315, 360, 70, "First liquidity", "If mint_lp.supply == 0 and both vaults are empty, the program uses max_x and max_y as the starting liquidity amounts.", fill=(255, 255, 255), accent=(65, 76, 92), body_size=9)
    c.box(430, 315, 360, 70, "Existing pool", "For later deposits, ConstantProduct::xy_deposit_amounts_from_l(vault_x, vault_y, lp_supply, amount, precision) computes the proportional token amounts.", fill=(255, 255, 255), accent=(65, 76, 92), body_size=9)

    rows = [
        ["Instruction", "Inputs", "What changes"],
        ["deposit(amount, max_x, max_y)", "amount = LP tokens user wants; max_x/max_y = upper token spend limits", "user_x and user_y decrease; vault_x and vault_y increase; user_lp increases"],
        ["LP relationship", "Example mental model: (Token A, Token B) => 1 LP share", "LP tracks ownership of the pool rather than being Token A or Token B itself"],
        ["Slippage guard", "amounts.x <= max_x and amounts.y <= max_y", "Deposit fails if required token amounts exceed the user's limits"],
    ]
    table(c, 36, 270, [170, 315, 285], rows, row_h=46)
    c.footer(2)
    pdf.add_page(c.content())


def page_3(pdf: Pdf) -> None:
    c = Canvas()
    c.header("Withdraw and Swap Flow", "Burn LP to exit liquidity; swap one token for the other through the vaults")
    c.text(36, 505, "Withdraw path", size=13, font="F2", color=(28, 39, 55))
    c.box(50, 414, 140, 62, "User LP", "User has LP tokens in user_lp.", fill=(255, 247, 239), accent=(173, 91, 31))
    c.arrow(190, 445, 230, 445)
    c.box(230, 414, 140, 62, "Burn LP", "burn_lp_tokens(amount) burns from user_lp.", fill=(252, 246, 246), accent=(160, 59, 64))
    c.arrow(370, 445, 410, 445)
    c.box(410, 414, 160, 62, "Calculate A + B", "xy_withdraw_amounts_from_l computes token output.", fill=(245, 250, 255), accent=(25, 88, 145))
    c.arrow(570, 445, 610, 445)
    c.box(610, 414, 150, 62, "Send tokens", "vault_x -> user_x and vault_y -> user_y.", fill=(239, 248, 240), accent=(53, 126, 72))

    c.text(36, 350, "Swap path", size=13, font="F2", color=(28, 39, 55))
    c.box(50, 262, 140, 62, "Trader input", "is_x=true means Token A/X goes in. false means Token B/Y goes in.", fill=(245, 247, 251), accent=(45, 55, 72))
    c.arrow(190, 293, 230, 293)
    c.box(230, 262, 150, 62, "Deposit input", "User token account transfers input token into the matching vault.", fill=(236, 246, 255), accent=(29, 100, 170))
    c.arrow(380, 293, 420, 293)
    c.box(420, 262, 160, 62, "Curve computes out", "ConstantProduct::swap(pair, amount, min) calculates output and fee.", fill=(248, 249, 244), accent=(78, 115, 34))
    c.arrow(580, 293, 620, 293)
    c.box(620, 262, 150, 62, "Withdraw output", "Opposite vault sends output token to the trader.", fill=(239, 248, 240), accent=(53, 126, 72))

    rows = [
        ["Flow", "Inputs", "Guard"],
        ["withdraw(amount, min_x, min_y)", "amount = LP to burn; min_x/min_y = minimum tokens to receive", "Fails if x < min_x or y < min_y"],
        ["swap(is_x, amount_in, min_amount_out)", "is_x chooses input side; amount_in is input; min_amount_out is output protection", "Fails if curve output is below min_amount_out"],
    ]
    table(c, 56, 190, [210, 370, 190], rows, row_h=44)
    c.footer(3)
    pdf.add_page(c.content())


def page_4(pdf: Pdf) -> None:
    c = Canvas()
    c.header("Accounts and Structs Needed", "Anchor account structs and the token accounts each instruction needs")

    rows1 = [
        ["Config field", "Meaning"],
        ["seed", "Pool seed used to derive the config PDA."],
        ["authority", "Optional authority that can control pool settings."],
        ["mint_x / mint_y", "Token A and Token B mints for this pool."],
        ["fee", "Swap fee in basis points."],
        ["locked", "If true, deposit/withdraw/swap should be blocked."],
        ["config_bump / lp_bump", "Bumps for config PDA and LP mint PDA."],
    ]
    table(c, 36, 500, [170, 600], rows1, row_h=30)

    rows2 = [
        ["Instruction struct", "Needed accounts"],
        ["Initialize", "initializer signer, mint_x, mint_y, mint_lp PDA, vault_x ATA, vault_y ATA, config PDA, token_program, associated_token_program, system_program"],
        ["Deposit", "user signer, mint_x, mint_y, config, mint_lp, vault_x, vault_y, user_x, user_y, user_lp, token_program, system_program, associated_token_program"],
        ["Withdraw", "user signer, mint_x, mint_y, config, mint_lp, vault_x, vault_y, user_x, user_y, user_lp, token_program, system_program, associated_token_program"],
        ["Swap", "user signer, mint_x, mint_y, config, mint_lp, vault_x, vault_y, user_x, user_y, token_program, system_program, associated_token_program"],
    ]
    table(c, 36, 285, [150, 620], rows2, row_h=54)

    c.box(36, 50, 370, 74, "PDA and token account rules", "config PDA: seeds [\"config\", seed]. LP mint PDA: seeds [\"lp\", config.key()]. Vault token accounts are ATAs owned by config. User token accounts are ATAs owned by user.", fill=(245, 250, 255), accent=(25, 88, 145), body_size=8.8)
    c.box(430, 50, 370, 74, "In plain English", "Liquidity providers deposit both tokens and receive LP. To exit, they burn LP and receive both tokens back. Swappers deposit one token and receive the other token from the pool.", fill=(248, 249, 244), accent=(78, 115, 34), body_size=8.8)
    c.footer(4)
    pdf.add_page(c.content())


def main() -> None:
    pdf = Pdf()
    page_1(pdf)
    page_2(pdf)
    page_3(pdf)
    page_4(pdf)
    pdf.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
