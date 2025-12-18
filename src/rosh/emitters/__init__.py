"""
Rosh Emitters - IR to Target Code Generators

Emitters are "mechanical translators" that convert IR to target code.
All semantic decisions are made in the IR transformer, not here.

Usage:
    from rosh.parser import Parser
    from rosh.lexer import Lexer
    from rosh.ir_transformer import transform_ast_to_ir
    from rosh.emitters.phaser import PhaserEmitter

    # Parse → Transform → Emit
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    ir = transform_ast_to_ir(ast)
    code = PhaserEmitter(ir).emit()
"""

from .base import BaseEmitter

__all__ = ['BaseEmitter']
