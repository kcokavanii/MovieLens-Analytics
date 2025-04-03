from collections import Counter
from datetime import datetime
import re
import pytest
import requests
from bs4 import BeautifulSoup
from collections import OrderedDict


class Links:
    """
    Analyzing data from links.csv
    """

    def __init__(self, filepath):
        self._filepath = filepath
        try:
            self.data = self._load_data()
        except Exception as e:
            print(f"Error initializing Links: {e}")
            self.data = []

    def _load_data(self):
        """
        Reads the CSV file and stores the data as a list of lists, where each inner list
        represents a row in the CSV file. Handles escaped commas within quotes.
        """
        data = []
        try:
            with open(self._filepath, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    row = re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', line)
                    row = [field.strip('"') for field in row]
                    movie = {
                        "movieId": row[0],
                        "imdbId": row[1],
                        "tmdbId": row[2],
                    }
                    data.append(movie)
        except FileNotFoundError:
            print(f"Error: File '{self._filepath}' not found.")
        except Exception as e:
            print(f"Error reading file '{self._filepath}': {e}")
        return data

    def get_imdb(self, list_of_movies, list_of_fields):
        """
        The method returns a list of lists [movieId, field1, field2, field3, ...]
        for the list of movies given as the argument (movieId).
        For example, [movieId, Director, Budget, Cumulative Worldwide Gross, Runtime].
        The values should be parsed from the IMDB webpages of the movies.
        Sort it by movieId descendingly.
        """
        # запросы долго обрабатываются
        imdb_data = []
        for movie in list_of_movies:
            imdb_id = movie.get("imdbId")
            if imdb_id:
                url = f"https://www.imdb.com/title/tt{str(imdb_id).zfill(7)}/"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0"
                }
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, "html.parser")
                    movie_data = [movie["movieId"]]
                    for field in list_of_fields:
                        field_value = self._extract_field(soup, field)
                        movie_data.append(field_value)
                    imdb_data.append(movie_data)
        imdb_data.sort(key=lambda x: int(x[0]), reverse=True)
        return imdb_data

    def top_directors(self, n):
        """
        The method returns a dict with top-n directors where the keys are directors and
        the values are numbers of movies created by them. Sort it by numbers descendingly.
        """
        try:
            list_of_movies = [{"movieId": movie["movieId"],
                               "imdbId": movie["imdbId"]} for movie in self.data]

            imdb_data = self.get_imdb(list_of_movies, ["Director"])
            directors_count = {}

            for data in imdb_data:
                director = data[1]
                if director and director != "N/A":
                    directors_count[director] = directors_count.get(
                        director, 0) + 1

            sorted_directors = sorted(
                directors_count.items(), key=lambda x: int(x[1]), reverse=True)
            top_directors = dict(sorted_directors[:n])

            return top_directors
        except Exception as e:
            print(f"Error in top_directors: {e}")
            return {}

    def most_expensive(self, n):
        """
        Returns a dictionary with the top-n most expensive movies based on their budgets.
        """
        return self.get_top_movies(
            fields=["Budget"],
            compute_value=lambda data: self._parse_budget(data[1]),
            n=n
        )

    def most_profitable(self, n):
        """
        Returns a dictionary with the top-n most profitable movies based on the difference
        between their worldwide gross and budget.
        """
        return self.get_top_movies(
            fields=["Budget", "Cumulative Worldwide Gross"],
            compute_value=lambda data: self._compute_profit(data[1], data[2]),
            n=n
        )

    def longest(self, n):
        """
        Returns a dictionary with the top-n longest movies based on their runtime.
        """
        return self.get_top_movies(
            fields=["Runtime"],
            compute_value=lambda data: self._parse_runtime(data[1]),
            n=n
        )

    def top_cost_per_minute(self, n):
        """
        Returns a dictionary with the top-n movies based on the cost per minute of their runtime.
        """
        return self.get_top_movies(
            fields=["Budget", "Runtime"],
            compute_value=lambda data: self._compute_cost_per_minute(
                data[1], data[2]),
            n=n
        )

    def get_top_movies(self, fields, compute_value, n):
        """
        Universal method to retrieve the top-n movies based on specific fields and calculations.
        """
        try:
            list_of_movies = [{"movieId": movie["movieId"],
                               "imdbId": movie["imdbId"]} for movie in self.data]
            imdb_data = self.get_imdb(list_of_movies, fields)
            results = {}
            list_of_movies = Links._load_movies()
            for data in imdb_data:
                movie_id = data[0]
                title = self.get_movie_title(movie_id, list_of_movies)
                if not title:
                    continue

                value = compute_value(data)
                if value is not None:
                    results[title] = value

            sorted_results = sorted(
                results.items(), key=lambda x: x[1], reverse=True)
            return dict(sorted_results[:n])
        except Exception as e:
            print(f"Error in get_top_movies: {e}")
            return {}

    def _parse_budget(self, budget):
        """
        Parses the budget string and converts it to a float.
        """
        if budget and "estimated" in budget:
            budget = budget.replace("(estimated)", "").replace(
                "$", "").replace(",", "").strip()
            try:
                return float(budget)
            except ValueError:
                return 0.0
        return 0.0

    def _parse_gross(self, gross):
        if gross:
            gross = gross.replace("$", "").replace(",", "").strip()
            try:
                return float(gross)
            except ValueError:
                return 0.0
        return 0.0

    def _parse_runtime(self, runtime):
        """
        Parses the runtime string and converts it to minutes.
        """
        if runtime:
            runtime = runtime.replace("h", "").replace("m", "").strip()
            try:
                hours, minutes = 0, 0
                if " " in runtime:
                    parts = runtime.split(" ")
                    hours = int(parts[0]) if parts[0].isdigit() else 0
                    minutes = int(parts[1]) if parts[1].isdigit() else 0
                elif runtime.isdigit():
                    minutes = int(runtime)
                return hours * 60 + minutes
            except ValueError:
                return 0
        return 0

    def _compute_profit(self, budget, gross):
        """
        Computes the profit as the difference between gross and budget.
        """
        budget = self._parse_budget(budget)
        gross = self._parse_gross(gross)
        return gross - budget

    def _compute_cost_per_minute(self, budget, runtime):
        """
        Computes the cost per minute based on budget and runtime.
        """
        budget = self._parse_budget(budget)
        runtime = self._parse_runtime(runtime)
        if budget > 0 and runtime > 0:
            return round(budget / runtime, 2)
        return None

    @staticmethod
    def _load_movies(filepath="data-folder/movies.csv"):
        """
        Reads the movies.csv file and stores the data as a list of dictionaries.
        Each dictionary represents a movie with keys: 'movieId', 'title', 'genres'.
        """
        movies = {}
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                next(file)
                for line in file:
                    line = line.strip()
                    row = re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', line)
                    row = [field.strip('"') for field in row]
                    if len(row) >= 3:
                        movies[row[0]] = row[1]
            return movies
        except FileNotFoundError:
            print(f"Error: File '{filepath}' not found.")
        except Exception as e:
            print(f"Error reading file '{filepath}': {e}")
        return []

    @staticmethod
    def get_movie_title(movie_id, list_of_movies):
        """
        The method returns the title of the movie for the given movieId from the movies.csv file.
        If the movieId is not found, it returns None.
        """
        try:
            ans = None
            if movie_id in list_of_movies:
                ans = list_of_movies[movie_id]
            return ans
        except Exception as e:
            print(f"Error in get_movie_title: {e}")
            return None

    def _extract_field(self, soup, field_name):
        """
        Extracts a specific field (e.g., Director, Budget, etc.) from the IMDb page soup object.
        """
        try:
            field_name = field_name.lower()
            field_value = "N/A"

            def get_text_from_tag(tag):
                return tag.text.strip() if tag else "N/A"

            base_class = "ipc-metadata-list__item"
            extra_class = " sc-1bec5ca1-2 eoigIp"
            content_class = "ipc-metadata-list-item__list-content-item"

            if field_name == "director":
                director_tag = soup.find(
                    "span", class_="ipc-metadata-list-item__label ipc-metadata-list-item__label--btn", string="Director"
                )
                if director_tag:
                    director = director_tag.find_parent("li").find("a")
                    field_value = get_text_from_tag(director)

            elif field_name == "runtime":
                runtime_tag = soup.find("li", class_="ipc-inline-list__item",
                                        string=lambda text: text and "h" in text and "m" in text)
                if runtime_tag:
                    field_value = runtime_tag.string.strip()

            elif field_name in ["cumulative worldwide gross", "budget"]:
                field_testid = "title-boxoffice-cumulativeworldwidegross" if field_name == "cumulative worldwide gross" else "title-boxoffice-budget"
                tag = soup.find(
                    "li", class_=base_class + extra_class,
                    attrs={"data-testid": field_testid}
                )
                if tag:
                    field_value = get_text_from_tag(
                        tag.find("span", class_=content_class))

            return field_value
        except Exception as e:
            print(f"Error extracting field '{field_name}': {e}")
            return "N/A"


class Movies:
    """
    Analyzing data from movies.csv
    """

    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self.read_data()

    def read_data(self):
        data = []
        try:
            with open(self.filepath, "r") as file:
                data = [line.strip().split(",") if ('"' not in line)
                        else line.strip().split('"') for line in file][1:]
        except FileNotFoundError:
            print(f"Error: File '{self.filepath}' not found.")
        except Exception as e:
            print(f"Error reading file '{self.filepath}': {e}")
        return data

    def dist_by_release(self):
        """
        The method returns a dict or an OrderedDict where the keys are years and the values are counts. 
        You need to extract years from the titles. Sort it by counts descendingly.
        """
        years = Counter([line[1][-5:-1]
                        for line in self.data if (line[1][-5:-1]).isdigit()])
        years = sorted(years.items(), key=lambda x: (-int(x[1]), -int(x[0])))
        release_years = OrderedDict(years)
        return release_years

    def dist_by_genres(self):
        """
        The method returns a dict where the keys are genres and the values are counts.
     Sort it by counts descendingly.
        """
        list_of_genres = [item.title() if "," not in item else item.replace(
            ",", "").title() for line in self.data for item in line[-1].split("|")]
        dict_genres = Counter(list_of_genres)
        dict_genres = sorted(dict_genres.items(), key=lambda x: -int(x[1]))
        genres = OrderedDict(dict_genres)
        return genres

    def most_genres(self, n):
        """
        The method returns a dict with top-n movies where the keys are movie titles and 
        the values are the number of genres of the movie. Sort it by numbers descendingly.
        """
        temp_movies = {}
        for line in self.data:
            temp_movies[line[1]] = len(line[-1].split("|"))
        temp_movies = sorted(temp_movies.items(),
                             key=lambda x: -int(x[1]))[:n:]
        movies = OrderedDict(temp_movies)
        return movies


class Ratings:
    """
    Analyzing data from ratings.csv
    """

    def __init__(self, path_to_the_file):
        self._filepath = path_to_the_file
        self._data = self.read_data()

    def read_data(self):
        data = []
        try:
            with open(self._filepath, "r") as file:
                file.readline()
                data = [line.strip().split(",") for line in file]
        except FileNotFoundError:
            print(f"Error: File '{self._filepath}' not found.")
        except Exception as e:
            print(f"Error reading file '{self._filepath}': {e}")
        return data

    class Movies:
        def dist_by_year(self):
            """
            The method returns a dict where the keys are years and the values are counts. 
            Sort it by years ascendingly. You need to extract years from timestamps.
            """
            c = Counter([datetime.fromtimestamp(
                int(i[3])).year for i in self._data])
            ratings_by_year = dict(sorted(c.items(), key=lambda x: x[0]))
            return ratings_by_year

        def dist_by_rating(self):
            """
            The method returns a dict where the keys are ratings and the values are counts.
         Sort it by ratings ascendingly.
            """
            c = Counter([float(i[2]) for i in self._data])
            ratings_distribution = dict(sorted(c.items(), key=lambda x: x[0]))
            return ratings_distribution

        def top_by_num_of_ratings(self, n, index_of_id=1):
            """
            The method returns top-n movies by the number of ratings. 
            It is a dict where the keys are movie titles and the values are numbers.
     Sort it by numbers descendingly.
            """
            if index_of_id == 0:                            # User ID
                c = Counter([i[0] for i in self._data])
            elif index_of_id == 1:
                list_of_movies = Links._load_movies()
                c = Counter([Links.get_movie_title(i[1], list_of_movies)
                            for i in self._data])
            else:
                raise AttributeError("Wrong index of column")
            top_movies = dict(sorted(c.most_common(
                n), key=lambda x: x[1], reverse=True))
            return top_movies

        @staticmethod
        def _average(lst):
            n = len(lst)
            if n == 0:
                raise ValueError("Error: List has 0 items")
            return sum(lst) / n

        @staticmethod
        def _median(lst):
            n = len(lst)
            lst = sorted(lst)
            if n == 0:
                raise ValueError("Error: List has 0 items")
            ans = 0
            if n % 2 == 1:
                ans = lst[n // 2]
            else:
                ans = (lst[n // 2 - 1] + lst[n // 2]) / 2
            return ans

        @staticmethod
        def _variance(lst):
            average = Ratings.Movies._average(lst)
            n = len(lst)
            return sum((lst[i] - average) ** 2 for i in range(n)) / n

        def create_list_of_ratings(self, index_of_id=1):
            d = dict()
            list_of_movies = Links._load_movies()
            for item in self._data:
                key = item[index_of_id]
                if index_of_id == 1:
                    key = Links.get_movie_title(key, list_of_movies)
                if not key in d:
                    d[key] = []
                d[key].append(float(item[2]))
            return d

        def top_by_ratings(self, n, metric="average", index_of_id=1):
            """
            The method returns top-n movies by the average or median of the ratings.
            It is a dict where the keys are movie titles and the values are metric values.
            Sort it by metric descendingly.
            The values should be rounded to 2 decimals.
            """
            if n < 0:
                n = 0
            funcs = {"average": self.Movies._average,
                     "median": self.Movies._median}

            d = self.Movies.create_list_of_ratings(self, index_of_id)

            for key in d:
                d[key] = round(funcs[metric](d[key]), 2)

            top_movies = sorted(d.items(), key=lambda x: x[1], reverse=True)
            return dict(top_movies[0:n])

        def top_controversial(self, n, index_of_id=1):
            """
            The method returns top-n movies by the variance of the ratings.
            It is a dict where the keys are movie titles and the values are the variances.
          Sort it by variance descendingly.
            The values should be rounded to 2 decimals.
            """
            if n < 0:
                n = 0

            d = self.Movies.create_list_of_ratings(self, index_of_id)

            for key in d:
                d[key] = round(self.Movies._variance(d[key]), 2)

            top_movies = sorted(d.items(), key=lambda x: x[1], reverse=True)
            return dict(top_movies[0:n])

    class Users:
        def top_by_num_of_ratings(self, n):
            return Ratings.Movies.top_by_num_of_ratings(self, n, 0)

        def top_by_ratings(self, n, metric="average"):
            return Ratings.Movies.top_by_ratings(self, n, metric, 0)

        def top_controversial(self, n):
            return Ratings.Movies.top_controversial(self, n, 0)


class Tags:
    """
    Analyzing data from tags.csv
    """

    def __init__(self, filepath):
        self._filepath = filepath
        try:
            self.data = self._load_data()
            self.tags = self._load_tags()
        except Exception as e:
            print(f"Error initializing Tags: {e}")
            self.data = []
            self.tags = []

    def _load_data(self):
        """
        Reads the CSV file and stores the data as a list of lists, where each inner list
        represents a row in the CSV file. Handles escaped commas within quotes.
        """
        data = []
        try:
            with open(self._filepath, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    row = re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', line)
                    row = [field.strip('"') for field in row]
                    data.append(row)
        except FileNotFoundError:
            print(f"Error: File '{self._filepath}' not found.")
        except Exception as e:
            print(f"Error reading file '{self._filepath}': {e}")
        return data

    def _load_tags(self):
        """
        Extracts unique tags from the loaded data.
        """
        try:
            tags = [row[2].strip() for row in self.data if len(row) > 2]
            return list(set(tags))
        except Exception as e:
            print(f"Error extracting tags: {e}")
            return []

    def most_words(self, n):
        """
        Returns the top-n tags with the most words. The result is a dictionary where
        the keys are tags and the values are the number of words in the tag.
        Duplicates are dropped, and results are sorted by word count in descending order.
        """
        try:
            word_counts = {tag: len(tag.split()) for tag in self.tags}
            sorted_tags = sorted(word_counts.items(),
                                 key=lambda x: x[1], reverse=True)
            return dict(sorted_tags[:n])
        except Exception as e:
            print(f"Error in most_words: {e}")
            return {}

    def longest(self, n):
        """
        Returns the top-n longest tags by character count. The result is a list of tags,
        sorted by length in descending order. Duplicates are removed.
        """
        try:
            sorted_tags = sorted(self.tags, key=len, reverse=True)
            return sorted_tags[:n]
        except Exception as e:
            print(f"Error in longest: {e}")
            return []

    def most_words_and_longest(self, n):
        """
        Returns the intersection of the top-n tags with the most words and the top-n
        longest tags by character count. The result is a list of tags.
        """
        try:
            most_words_tags = set(self.most_words(n).keys())
            longest_tags = set(self.longest(n))
            return list(most_words_tags & longest_tags)
        except Exception as e:
            print(f"Error in most_words_and_longest: {e}")
            return []

    def most_popular(self, n):
        """
        Returns the most popular tags, where popularity is determined by the frequency of
        each tag in the CSV file. The result is a dictionary where the keys are tags and
        the values are the number of occurrences of each tag. Results are sorted by frequency in descending order.
        """
        try:
            tag_counts = {}
            tag_original = {}

            for row in self.data:
                if len(row) > 2:
                    tag = row[2].strip()
                    tag_lower = tag.lower()

                    tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1
                    tag_original[tag_lower] = tag
            sorted_tags = sorted(tag_counts.items(),
                                 key=lambda x: x[1], reverse=True)
            return {tag_original[tag_lower]: count for tag_lower, count in sorted_tags[:n]}
        except Exception as e:
            print(f"Error in most_popular: {e}")
            return {}

    def tags_with(self, word):
        """
        Returns all unique tags that contain the specified word (case insensitive).
        Duplicates are removed, and the result is sorted alphabetically.
        """
        try:
            filtered_tags = [
                tag for tag in self.tags if word.lower() in tag.lower()]
            return sorted(filtered_tags)
        except Exception as e:
            print(f"Error in tags_with: {e}")
            return []


class Tests:

    # ---------------------------------------
    # Tests for Tags class
    # ---------------------------------------

    @pytest.fixture
    def sample_tags(self):
        sample_data = """userId,movieId,tag,timestamp
2,60756,funny,1445714994
2,60756,Highly quotable,1445714996
2,60756,will ferrell,1445714992
2,89774,Boxing story,1445715207
2,89774,MMA,1445715200
2,89774,Tom Hardy,1445715205
2,106782,drugs,1445715054"""
        filepath = "sample_tags.csv"
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(sample_data)
        return Tags(filepath)

    def test_most_words(self, sample_tags):
        result = sample_tags.most_words(3)
        assert isinstance(result, dict)
        assert all(isinstance(key, str)
                   for key in result.keys())
        assert all(isinstance(value, int) for value in result.values()
                   )
        assert list(result.values()) == sorted(
            result.values(), reverse=True
        )

    def test_longest(self, sample_tags):
        result = sample_tags.longest(3)
        assert isinstance(result, list)
        assert all(isinstance(tag, str)
                   for tag in result)
        assert result == sorted(
            result, key=len, reverse=True)

    def test_most_words_and_longest(self, sample_tags):
        result = sample_tags.most_words_and_longest(3)
        assert isinstance(result, list)
        assert all(isinstance(tag, str)
                   for tag in result)

    def test_most_popular(self, sample_tags):
        result = sample_tags.most_popular(3)
        assert isinstance(result, dict)
        assert all(isinstance(key, str)
                   for key in result.keys())
        assert all(isinstance(value, int) for value in result.values()
                   )
        assert list(result.values()) == sorted(
            result.values(), reverse=True
        )

    def test_tags_with(self, sample_tags):
        result = sample_tags.tags_with("funny")
        assert isinstance(result, list)
        assert all(isinstance(tag, str)
                   for tag in result)
        assert result == sorted(
            result)

    def test_tags_with_case_insensitivity(self, sample_tags):
        result = sample_tags.tags_with("FUNNY")
        assert isinstance(result, list)
        assert "funny" in result

    # ---------------------------------------
    # Tests for Ratings class
    # ---------------------------------------

    @staticmethod
    def test_RatingsMovies_dist_by_year():
        r = Ratings("data-folder/ratings.csv")
        d = Ratings.Movies.dist_by_year(r)
        assert type(d) == type(dict())
        keys = tuple(d.keys())
        assert all(keys[i - 1] <= keys[i] for i in range(1, len(keys)))

    @staticmethod
    def test_RatingsMovies_dist_by_rating():
        r = Ratings("data-folder/ratings.csv")
        d = Ratings.Movies.dist_by_year(r)
        assert type(d) == type(dict())
        keys = tuple(d.keys())
        assert all(keys[i - 1] <= keys[i] for i in range(1, len(keys)))

    @staticmethod
    def test_RatingsMovies_top_by_num_of_ratings():
        r = Ratings("data-folder/ratings.csv")
        d = Ratings.Movies.top_by_num_of_ratings(r, 10)
        assert type(d) == type(dict())
        values = tuple(d.values())
        assert all(values[i - 1] >= values[i] for i in range(1, len(values)))

    @staticmethod
    def test_RatingsMovies_top_by_ratings():
        r = Ratings("data-folder/ratings.csv")
        num_of_top = 1000
        d1 = Ratings.Movies.top_by_ratings(r, num_of_top, metric="median")
        d2 = Ratings.Movies.top_by_ratings(r, num_of_top)
        assert type(d1) == type(dict())
        assert type(d2) == type(dict())
        values = tuple(d1.values())
        assert all(values[i - 1] >= values[i] for i in range(1, len(values)))
        values = tuple(d2.values())
        assert all(values[i - 1] >= values[i] for i in range(1, len(values)))
        assert len(d1) == len(d2) == num_of_top or num_of_top > len(d1)

    @staticmethod
    def test_RatingsMovies_top_controversial():
        r = Ratings("data-folder/ratings.csv")
        num_of_top = 100
        d = Ratings.Movies.top_controversial(r, num_of_top)
        assert type(d) == type(dict())
        values = tuple(d.values())
        assert all(values[i - 1] >= values[i] for i in range(1, len(values)))
        assert num_of_top == len(d)

    @staticmethod
    def test_RatingsMovies_average():
        lst = [1, 1, 5, 2, 6, 2]
        func_ans = Ratings.Movies._average(lst)
        ans = sum(lst) / len(lst)
        assert func_ans == ans

    @staticmethod
    def test_RatingsMovies_median_even():
        lst = [1, 1, 2, 2, 5, 7]
        n = len(lst)
        func_ans = Ratings.Movies._median(lst)
        ans = (lst[n // 2 - 1] + lst[n // 2]) / 2
        assert func_ans == ans

    @staticmethod
    def test_RatingsMovies_median_odd():
        lst = [1, 1, 2, 5, 7]
        func_ans = Ratings.Movies._median(lst)
        ans = lst[len(lst) // 2]
        assert func_ans == ans

    @staticmethod
    def test_RatingsMovies_variance():
        lst = [1, 1, 5, 2, 6, 2]
        n = len(lst)
        avg = sum(lst) / n
        func_ans = Ratings.Movies._variance(lst)
        ans = sum((i - avg) ** 2 for i in lst) / n
        assert func_ans == ans

    @staticmethod
    def test_RatingsUsers_top_by_num_of_ratings():
        r = Ratings("data-folder/ratings.csv")
        d = Ratings.Users.top_by_num_of_ratings(r, 10)
        assert type(d) == type(dict())
        values = tuple(d.values())
        assert all(values[i - 1] >= values[i] for i in range(1, len(values)))

    @staticmethod
    def test_RatingsUsers_top_by_ratings():
        r = Ratings("data-folder/ratings.csv")
        num_of_top = 1000
        d1 = Ratings.Users.top_by_ratings(r, num_of_top, metric="median")
        d2 = Ratings.Users.top_by_ratings(r, num_of_top)
        assert type(d1) == type(dict())
        assert type(d2) == type(dict())
        values = tuple(d1.values())
        assert all(values[i - 1] >= values[i] for i in range(1, len(values)))
        values = tuple(d2.values())
        assert all(values[i - 1] >= values[i] for i in range(1, len(values)))
        assert len(d1) == len(d2) == num_of_top or num_of_top > len(d1)

    @staticmethod
    def test_RatingsUsers_top_controversial():
        r = Ratings("data-folder/ratings.csv")
        num_of_top = 100
        d = Ratings.Users.top_controversial(r, num_of_top)
        assert type(d) == type(dict())
        values = tuple(d.values())
        assert all(values[i - 1] >= values[i] for i in range(1, len(values)))
        assert num_of_top == len(d)

    # ---------------------------------------
    # Tests for Movies class
    # ---------------------------------------

    @staticmethod
    def test_Movies_dist_by_release():
        years = Movies("data-folder/movies.csv")
        result = years.dist_by_release()
        keys = tuple(result.keys())
        values = tuple(result.values())
        assert isinstance(result, dict)
        assert all(isinstance(i, str) for i in keys)
        assert all(isinstance(i, int) for i in values)
        assert all(values[i - 1] >= values[i] for i in range(1, len(values)))

    @staticmethod
    def test_Movies_dist_by_genres():
        genres = Movies("data-folder/movies.csv")
        result = genres.dist_by_genres()
        assert isinstance(result, dict)
        keys = tuple(result.keys())
        values = tuple(result.values())
        assert isinstance(result, dict)
        assert all(isinstance(i, str) for i in keys)
        assert all(isinstance(i, int) for i in values)
        assert all(values[i - 1] >= values[i] for i in range(1, len(values)))

    @staticmethod
    def test_Movies_most_genres():
        m_genres = Movies("data-folder/movies.csv")
        result = m_genres.most_genres(10)
        assert isinstance(result, dict)
        keys = tuple(result.keys())
        values = tuple(result.values())
        assert isinstance(result, dict)
        assert all(isinstance(i, str) for i in keys)
        assert all(isinstance(i, int) for i in values)
        assert all(values[i - 1] >= values[i] for i in range(1, len(values)))
        assert len(keys) == len(values) == 10

    # ---------------------------------------
    # Tests for Links class
    # ---------------------------------------

    @pytest.fixture
    def sample_links(self):
        sample_data = """movieId,imdbId,tmdbId
1,0114709,862
2,0113497,8844
3,0113228,15602"""
        filepath = "sample_links.csv"
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(sample_data)
        return Links(filepath)

    @staticmethod
    def test_get_imdb(sample_links: Links):
        list_of_movies = [{"movieId": movie["movieId"],
                           "imdbId": movie["imdbId"]} for movie in sample_links.data]
        list_of_fields = ["Director"]
        ans = sample_links.get_imdb(list_of_movies, list_of_fields)
        assert len(ans) == 3
        assert isinstance(ans, list)
        assert isinstance(ans[0], list)
        assert all(len(item) == 2 for item in ans)
        assert all(int(ans[i - 1][0]) > int(ans[i][0])
                   for i in range(1, len(ans)))
        assert ans == [['3', 'Howard Deutch'], [
            '2', 'Joe Johnston'], ['1', 'John Lasseter']]

    @staticmethod
    def test_top_directors(sample_links: Links):
        n = 3
        ans = sample_links.top_directors(n)
        assert isinstance(ans, dict)
        assert len(ans) == n

    @staticmethod
    def test_most_expensive(sample_links: Links):
        n = 3
        ans = sample_links.most_expensive(n)
        assert isinstance(ans, dict)
        assert len(ans) == n

    @staticmethod
    def test_most_profitable(sample_links: Links):
        n = 3
        ans = sample_links.most_profitable(n)
        assert isinstance(ans, dict)
        assert len(ans) == n

    @staticmethod
    def test_longest(sample_links: Links):
        n = 3
        ans = sample_links.longest(n)
        assert isinstance(ans, dict)
        assert len(ans) == n

    @staticmethod
    def test_top_cost_per_minute(sample_links: Links):
        n = 3
        ans = sample_links.top_cost_per_minute(n)
        assert isinstance(ans, dict)
        assert len(ans) == n
