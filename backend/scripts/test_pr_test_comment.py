import allure

from scripts.pr_test_comment import classify_source


@allure.epic("Tooling")
@allure.feature("Pull request report")
@allure.story("New and updated tests")
class PullRequestCommentTests:
    @allure.title("The pull request comment separates new tests from updated tests")
    @allure.description(
        "What: a test function that did not exist on the base branch is new, "
        "and a test function whose body changed is updated. An untouched "
        "test is omitted.\n\n"
        "Why: the pull request should show the tests this branch added or "
        "edited, not the whole suite."
    )
    @allure.severity(allure.severity_level.NORMAL)
    def test_classifies_added_and_edited_tests(self) -> None:
        base = (
            "def test_ready():\n"
            "    assert True\n"
            "\n"
            "def test_same():\n"
            "    assert 1 == 1\n"
        )
        head = (
            "def test_ready():\n"
            "    assert False\n"
            "\n"
            "def test_same():\n"
            "    assert 1 == 1\n"
            "\n"
            "def test_added():\n"
            "    assert True\n"
        )

        with allure.step("Compare a file that adds one test and edits another"):
            new, updated = classify_source(base, head)

        with allure.step("Expect only the added and edited tests"):
            assert new == ["test_added"]
            assert updated == ["test_ready"]

    @allure.title("A decorator change counts as an updated test")
    @allure.description(
        "What: adding or editing a decorator on an existing test marks that "
        "test as updated.\n\n"
        "Why: Allure titles, descriptions, and steps live on decorators. A "
        "change there changes what the report says about the test."
    )
    def test_counts_a_decorator_change_as_an_update(self) -> None:
        base = "def test_ready():\n    assert True\n"
        head = "@mark\ndef test_ready():\n    assert True\n"

        with allure.step("Compare a test whose only change is a decorator"):
            new, updated = classify_source(base, head)

        with allure.step("Expect an update and no new test"):
            assert new == []
            assert updated == ["test_ready"]

    @allure.title("Every test in a new file is new")
    @allure.description(
        "What: when the base branch has no copy of the file, each test in "
        "it is new, including a test that lives on a class.\n\n"
        "Why: the first pull request that adds a test module should list "
        "those tests, with the class name so two modules cannot collide."
    )
    def test_treats_every_test_as_new_when_the_file_is_new(self) -> None:
        head = "class HealthTests:\n    def test_ready(self):\n        assert True\n"

        with allure.step("Classify a file that does not exist on the base"):
            new, updated = classify_source(None, head)

        with allure.step("Expect the class test to be new"):
            assert new == ["HealthTests.test_ready"]
            assert updated == []
