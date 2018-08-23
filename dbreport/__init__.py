import sqlite3 as sq3
import os
from jinja2 import Template, Environment, FileSystemLoader
from datetime import datetime
import json


class Report(object):
    """Object that will define a report"""
    def __init__(self, layout_path):
        self.path = layout_path
        with open(layout_path, 'r') as f:
            self.layout = json.loads(f.read())
        self.layout = self.__set_defaults()
        self.paths = self.layout['paths']
        self.cursor = sq3.connect(self.paths['database']).cursor()
        self.categories = self.__get_categries()
        self.env = Environment(trim_blocks=True, lstrip_blocks=True,
                  loader=FileSystemLoader(self.paths['template_dir']))

    @staticmethod
    def __read_file(filename):
        """return the sql for the given file"""
        with open(filename, 'r') as f:
            return f.read()

    def get_views(self):
        """return a list of view names from database"""
        filename = os.path.join(self.paths['sql'][0], 'get_views.sql')
        data = self.__get_data(filename)
        views = [view[0] for view in data]

        # Remove any views that are in the ingore list in the layout
        # file
        ignore_views = self.layout['ignore_views']
        for ignore_view in ignore_views:
            if ignore_view in views:
                views.remove(ignore_view)
        return views

    def __get_data(self, filename):
        """return cursor object of data"""
        sql = self.__read_file(filename)
        return self.cursor.execute(sql)

    def get_all_data(self):
        """return a dictionary containing all the data for all views"""
        views = self.get_views()
        data = {}
        for view in views:
            sql = '''SELECT * FROM {}'''.format(view)
            results = self.cursor.execute(sql)
            rows = [result for result in results]
            data.setdefault(view, rows)
        return data

    def __get_columns(self, table_name):
        """return a list of columns for the given table"""
        sql = '''PRAGMA table_info("{}")'''
        sql = sql.format(table_name)
        c = self.cursor.execute(sql)
        cols = []
        cols = [col[1] for col in c]
        return cols

    def __get_title(self, view_names):
        """return the name/title to be used as the page title"""
        map_names = self.layout['titles']
        titles = []
        if type(view_names) is list:
            for view in view_names:
                titles.append(map_names.get(view, view))
        else:
            titles = map_names.get(view_names, view_names)
        return titles

    def __get_misc(self):
        """
        Update the categories to include a Misc category that will
        include all views in the database that is not specified in
        another category. This will ensure that there will be a
        convenient way to access all reports from the navigation bar
        in each report.
        """
        categories = self.layout['categories']
        views = self.get_views()
        for category in categories:
            for view in categories[category]:
                if view in views:
                    views.remove(view)
        categories.setdefault('Misc', views)
        return categories

    def __get_categries(self):
        """
        Given the category name and list of view names, return
        a dictionary with category name and list of relative paths to
        the report for that view
        """
        cat_list = self.__get_misc()
        categories = {}
        for key in cat_list:
            paths = []
            titles = self.__get_title(cat_list[key])
            for link in cat_list[key]:
                # Note all the reports are all in the same folder
                path = os.path.join('.', link + '.html')
                paths.append(path)
                val = [titles, paths]
            categories.setdefault(key, val)

        return categories

    def render_report(self, view_name):
        """render an output report"""

        # Set up basic constants for this report
        update = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        report_dir = self.paths['report_dir']
        css_styles = self.paths['css_styles']
        js = self.paths['javascript']
        headers = self.__get_columns(view_name)
        caption = self.layout['captions'].get(view_name, "")
        title = self.__get_title(view_name)
        description = self.layout['descriptions'].get(view_name, "")
        categories = self.categories

        # Query database for all rows for view given by input
        data = self.get_all_data()
        rows = [row for row in data[view_name]]

        # Get the template for reports and render
        temp = self.env.get_template(self.paths['template'])
        html = temp.render(title=title,
                           description=description,
                           categories=categories,
                           updated=update,
                           caption=caption,
                           css_styles=css_styles,
                           javascripts=js,
                           headers=headers,
                           rows=rows)

        # Write rendered template to file in reports directory
        filename = '{}.html'.format(view_name)
        with open(os.path.join(report_dir, filename), 'w') as f:
            f.write(html)

    def render_all(self):
        """render report for all views in database"""
        views = self.get_views()
        for view in views:
            self.render_report(view)

    def __set_settings(self, default, new):

        for key in default:
            new.setdefault(key, default[key])
            if type(default[key]) == type({}):
                new[key] = self.__set_settings(default[key], new[key])
        return new

    def __set_defaults(self):
        """get default paths. If the path is in the specified layout
        file, that path should be used, otherwise fall back and use the
        default"""
        # Get default path to the package layout file
        package_path = __file__
        for i in range(2):
            package_path = os.path.dirname(package_path)
        default_path = os.path.join(package_path,
                                    'templates', 'layout.json')
        with open(default_path, 'r') as f:
            default = json.loads(f.read())

        # expand paths in default layout to be absolulte
        template_dir = os.path.join(package_path,
                                    default['paths']['template_dir'][0])
        default['paths']['template_dir'] = template_dir
        for p in ['css_styles', 'javascript', 'sql']:
            paths = []
            for path in default['paths'][p]:
                paths.append(os.path.join(template_dir, path))
            default['paths'][p] = paths

        # Set layout file to use defaults and have user specified file
        # overwrite any settings.
        layout = self.__set_settings(default, self.layout)
        return layout


def main():
    print('this is the main function')


if __name__ == '__main__':
    main()
