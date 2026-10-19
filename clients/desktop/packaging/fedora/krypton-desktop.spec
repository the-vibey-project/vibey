# Declared only: not published to Fedora COPR until the operator decides (see clients/desktop/PACKAGING.md).
Name:           krypton-desktop
Version:        0.1.0
Release:        1%{?dist}
Summary:        The desktop app for krypton
License:        MIT
URL:            https://github.com/the-vibey-project/vibey
Source0:        %{url}/archive/refs/tags/krypton-desktop-v%{version}.tar.gz

BuildRequires:  gcc
BuildRequires:  meson
BuildRequires:  pkgconfig(gtk4)
BuildRequires:  pkgconfig(libadwaita-1)
BuildRequires:  pkgconfig(libsoup-3.0)
BuildRequires:  pkgconfig(json-glib-1.0)
BuildRequires:  pkgconfig(avahi-client)
BuildRequires:  pkgconfig(avahi-glib)
# GIO's TLS backend and the openssl CLI: the hub client's pinning tests in %%check need both.
BuildRequires:  glib-networking
BuildRequires:  openssl
Requires:       glib-networking

%description
krypton desktop: the GTK 4 and libadwaita client for a vibey hub.

%prep
%autosetup -n vibey-krypton-desktop-v%{version}

%build
cd clients/desktop
%meson
%meson_build

%install
cd clients/desktop
%meson_install

%check
cd clients/desktop
%meson_test

%files
%license LICENSE
%{_bindir}/krypton-desktop
%{_datadir}/applications/io.github.the_vibey_project.krypton.desktop
%{_metainfodir}/io.github.the_vibey_project.krypton.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/io.github.the_vibey_project.krypton.svg
