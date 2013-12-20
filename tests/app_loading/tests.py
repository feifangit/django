from __future__ import unicode_literals

import os
import sys
from unittest import TestCase
import warnings

from django.core.apps import app_cache
from django.core.apps.cache import AppCache
from django.test.utils import override_settings
from django.utils._os import upath
from django.utils import six


class EggLoadingTest(TestCase):

    def setUp(self):
        self.old_path = sys.path[:]
        self.egg_dir = '%s/eggs' % os.path.dirname(upath(__file__))

        # The models need to be removed after the test in order to prevent bad
        # interactions with the flush operation in other tests.
        self._old_models = app_cache.app_configs['app_loading'].models.copy()

    def tearDown(self):
        app_cache.app_configs['app_loading'].models = self._old_models
        app_cache.all_models['app_loading'] = self._old_models
        app_cache._get_models_cache = {}

        sys.path = self.old_path

    def test_egg1(self):
        """Models module can be loaded from an app in an egg"""
        egg_name = '%s/modelapp.egg' % self.egg_dir
        sys.path.append(egg_name)
        with app_cache._with_app('app_with_models'):
            models_module = app_cache.get_app_config('app_with_models').models_module
            self.assertIsNotNone(models_module)

    def test_egg2(self):
        """Loading an app from an egg that has no models returns no models (and no error)"""
        egg_name = '%s/nomodelapp.egg' % self.egg_dir
        sys.path.append(egg_name)
        with app_cache._with_app('app_no_models'):
            models_module = app_cache.get_app_config('app_no_models').models_module
            self.assertIsNone(models_module)

    def test_egg3(self):
        """Models module can be loaded from an app located under an egg's top-level package"""
        egg_name = '%s/omelet.egg' % self.egg_dir
        sys.path.append(egg_name)
        with app_cache._with_app('omelet.app_with_models'):
            models_module = app_cache.get_app_config('app_with_models').models_module
            self.assertIsNotNone(models_module)

    def test_egg4(self):
        """Loading an app with no models from under the top-level egg package generates no error"""
        egg_name = '%s/omelet.egg' % self.egg_dir
        sys.path.append(egg_name)
        with app_cache._with_app('omelet.app_no_models'):
            models_module = app_cache.get_app_config('app_no_models').models_module
            self.assertIsNone(models_module)

    def test_egg5(self):
        """Loading an app from an egg that has an import error in its models module raises that error"""
        egg_name = '%s/brokenapp.egg' % self.egg_dir
        sys.path.append(egg_name)
        with six.assertRaisesRegex(self, ImportError, 'modelz'):
            with app_cache._with_app('broken_app'):
                app_cache.get_app_config('omelet.app_no_models').models_module

    def test_missing_app(self):
        """
        Test that repeated app loading doesn't succeed in case there is an
        error. Refs #17667.
        """
        app_cache = AppCache()
        # Pretend we're the master app cache to test the population process.
        app_cache._apps_loaded = False
        app_cache._models_loaded = False
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", "Overriding setting INSTALLED_APPS")
            with override_settings(INSTALLED_APPS=['notexists']):
                with self.assertRaises(ImportError):
                    app_cache.get_model('notexists', 'nomodel')
                with self.assertRaises(ImportError):
                    app_cache.get_model('notexists', 'nomodel')


class GetModelsTest(TestCase):
    def setUp(self):
        from .not_installed import models
        self.not_installed_module = models

    def test_get_model_only_returns_installed_models(self):
        self.assertEqual(
            app_cache.get_model("not_installed", "NotInstalledModel"), None)

    def test_get_model_with_not_installed(self):
        self.assertEqual(
            app_cache.get_model(
                "not_installed", "NotInstalledModel", only_installed=False),
            self.not_installed_module.NotInstalledModel)

    def test_get_models_only_returns_installed_models(self):
        self.assertNotIn(
            "NotInstalledModel",
            [m.__name__ for m in app_cache.get_models()])

    def test_get_models_with_app_label_only_returns_installed_models(self):
        self.assertEqual(app_cache.get_models(self.not_installed_module), [])

    def test_get_models_with_not_installed(self):
        self.assertIn(
            "NotInstalledModel",
            [m.__name__ for m in app_cache.get_models(only_installed=False)])


class NotInstalledModelsTest(TestCase):
    def test_related_not_installed_model(self):
        from .not_installed.models import NotInstalledModel
        self.assertEqual(
            set(NotInstalledModel._meta.get_all_field_names()),
            set(["id", "relatedmodel", "m2mrelatedmodel"]))