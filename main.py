from app import (
    create_app,
    debugging_add_to_db,
    db,
    init_db,
    debugging_add_sessions_to_cust,
)

app = create_app()


if __name__ == "__main__":
    # When we run the app, we create our db tables for that instance.
    with app.app_context():
        # refresh db every run if in debug
        if app.config["DEBUG"]:
            db.drop_all()
            db.create_all()
            init_db(db)
            try:
                debugging_add_to_db(db)
                debugging_add_sessions_to_cust(db)
            except BaseException as e:
                print(e)
        else:
            try:
                db.create_all()
                init_db(db)
            except BaseException as e:
                print(e)
    app.run()
