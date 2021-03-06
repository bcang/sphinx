"""
    sphinx.domains.rst
    ~~~~~~~~~~~~~~~~~~

    The reStructuredText domain.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.locale import _
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode

if False:
    # For type annotation
    from typing import Any, Dict, Iterator, List, Tuple  # NOQA
    from docutils import nodes  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA


dir_sig_re = re.compile(r'\.\. (.+?)::(.*)$')


class ReSTMarkup(ObjectDescription):
    """
    Description of generic reST markup.
    """

    def add_target_and_index(self, name, sig, signode):
        # type: (str, str, addnodes.desc_signature) -> None
        targetname = self.objtype + '-' + name
        if targetname not in self.state.document.ids:
            signode['names'].append(targetname)
            signode['ids'].append(targetname)
            signode['first'] = (not self.names)
            self.state.document.note_explicit_target(signode)

            objects = self.env.domaindata['rst']['objects']
            key = (self.objtype, name)
            if key in objects:
                self.state_machine.reporter.warning(
                    'duplicate description of %s %s, ' % (self.objtype, name) +
                    'other instance in ' + self.env.doc2path(objects[key]),
                    line=self.lineno)
            objects[key] = self.env.docname
        indextext = self.get_index_text(self.objtype, name)
        if indextext:
            self.indexnode['entries'].append(('single', indextext,
                                              targetname, '', None))

    def get_index_text(self, objectname, name):
        # type: (str, str) -> str
        if self.objtype == 'directive':
            return _('%s (directive)') % name
        elif self.objtype == 'role':
            return _('%s (role)') % name
        return ''


def parse_directive(d):
    # type: (str) -> Tuple[str, str]
    """Parse a directive signature.

    Returns (directive, arguments) string tuple.  If no arguments are given,
    returns (directive, '').
    """
    dir = d.strip()
    if not dir.startswith('.'):
        # Assume it is a directive without syntax
        return (dir, '')
    m = dir_sig_re.match(dir)
    if not m:
        return (dir, '')
    parsed_dir, parsed_args = m.groups()
    return (parsed_dir.strip(), ' ' + parsed_args.strip())


class ReSTDirective(ReSTMarkup):
    """
    Description of a reST directive.
    """
    def handle_signature(self, sig, signode):
        # type: (str, addnodes.desc_signature) -> str
        name, args = parse_directive(sig)
        desc_name = '.. %s::' % name
        signode += addnodes.desc_name(desc_name, desc_name)
        if len(args) > 0:
            signode += addnodes.desc_addname(args, args)
        return name


class ReSTRole(ReSTMarkup):
    """
    Description of a reST role.
    """
    def handle_signature(self, sig, signode):
        # type: (str, addnodes.desc_signature) -> str
        signode += addnodes.desc_name(':%s:' % sig, ':%s:' % sig)
        return sig


class ReSTDomain(Domain):
    """ReStructuredText domain."""
    name = 'rst'
    label = 'reStructuredText'

    object_types = {
        'directive': ObjType(_('directive'), 'dir'),
        'role':      ObjType(_('role'),      'role'),
    }
    directives = {
        'directive': ReSTDirective,
        'role':      ReSTRole,
    }
    roles = {
        'dir':  XRefRole(),
        'role': XRefRole(),
    }
    initial_data = {
        'objects': {},  # fullname -> docname, objtype
    }  # type: Dict[str, Dict[str, Tuple[str, ObjType]]]

    def clear_doc(self, docname):
        # type: (str) -> None
        for (typ, name), doc in list(self.data['objects'].items()):
            if doc == docname:
                del self.data['objects'][typ, name]

    def merge_domaindata(self, docnames, otherdata):
        # type: (List[str], Dict) -> None
        # XXX check duplicates
        for (typ, name), doc in otherdata['objects'].items():
            if doc in docnames:
                self.data['objects'][typ, name] = doc

    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        # type: (BuildEnvironment, str, Builder, str, str, addnodes.pending_xref, nodes.Element) -> nodes.Element  # NOQA
        objects = self.data['objects']
        objtypes = self.objtypes_for_role(typ)
        for objtype in objtypes:
            if (objtype, target) in objects:
                return make_refnode(builder, fromdocname,
                                    objects[objtype, target],
                                    objtype + '-' + target,
                                    contnode, target + ' ' + objtype)
        return None

    def resolve_any_xref(self, env, fromdocname, builder, target, node, contnode):
        # type: (BuildEnvironment, str, Builder, str, addnodes.pending_xref, nodes.Element) -> List[Tuple[str, nodes.Element]]  # NOQA
        objects = self.data['objects']
        results = []  # type: List[Tuple[str, nodes.Element]]
        for objtype in self.object_types:
            if (objtype, target) in self.data['objects']:
                results.append(('rst:' + self.role_for_objtype(objtype),
                                make_refnode(builder, fromdocname,
                                             objects[objtype, target],
                                             objtype + '-' + target,
                                             contnode, target + ' ' + objtype)))
        return results

    def get_objects(self):
        # type: () -> Iterator[Tuple[str, str, str, str, str, int]]
        for (typ, name), docname in self.data['objects'].items():
            yield name, name, typ, docname, typ + '-' + name, 1


def setup(app):
    # type: (Sphinx) -> Dict[str, Any]
    app.add_domain(ReSTDomain)

    return {
        'version': 'builtin',
        'env_version': 1,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
