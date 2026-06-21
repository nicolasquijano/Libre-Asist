"""Compatibility wrappers around advanced LibreOffice skills."""

import skills


def chat(user_prompt, ctx):
    return skills.route("chat", user_prompt, ctx)


def formula(user_prompt, ctx):
    return skills.route("formula", user_prompt, ctx)


def calc_format(user_prompt, ctx):
    return skills.route("format", user_prompt, ctx)


def explain(ctx):
    return skills.route("analyze", "", ctx)


def analyze(ctx):
    return skills.route("analyze", "", ctx)


def clean(ctx):
    return skills.route("clean", "", ctx)


def preview(user_prompt, ctx):
    return skills.route("preview", user_prompt, ctx)


def writer_explain(ctx):
    return skills.writer_review("Analyze and explain the text without modifying it.", ctx)


def writer_review(user_prompt, ctx):
    return skills.writer_review(user_prompt, ctx)


def writer_rewrite(user_prompt, ctx):
    return skills.writer_rewrite(user_prompt, ctx)


def writer_preview(user_prompt, ctx):
    return skills.writer_preview(user_prompt, ctx)
