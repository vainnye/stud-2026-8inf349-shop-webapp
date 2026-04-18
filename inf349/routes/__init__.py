def register_blueprints(app):
    """Register all Flask blueprints on the given app."""
    from .products import bp as products_bp

    app.register_blueprint(products_bp)
