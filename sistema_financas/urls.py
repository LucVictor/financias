from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('contas/', include('contas.urls')),
    path('cartoes/', include('cartoes.urls')),
    path('dividas/', include('dividas.urls')),
    path('poupanca/', include('poupanca.urls')),
    path('renda-fixa/', include('renda_fixa.urls')),
    path('ativos/', include('renda_variavel.urls')),
    path('cripto/', include('cripto.urls')),
    path('fluxo/', include('contas_periodicas.urls')),
    path('assistente/', include('assistente.urls')),
    path('accounts/login/',
         auth_views.LoginView.as_view(template_name='registration/login.html'),
         name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)