import os
import sys
import csv
from push_api import SalesforcePushApi

# Force UTF8 output
reload(sys)
sys.setdefaultencoding('UTF8')

if __name__ == '__main__':
    try:
        
        username = os.environ.get('SF_USERNAME')
        password = os.environ.get('SF_PASSWORD')
        serverurl = os.environ.get('SF_SERVERURL')
        version_id = os.environ.get('VERSION')
        greater_than_version_id = os.environ.get('GREATER_THAN_VERSION', None)
        subscriber_where = os.environ.get('SUBSCRIBER_WHERE', None)

        # Add standard filters for only active orgs
        default_where = {'PackageSubscriber': "OrgStatus = 'Active' AND InstalledStatus = 'i'"}

        # Append subscriber where if passed in environment
        if subscriber_where:
            default_where['PackageSubscriber'] += " AND (%s)" % subscriber_where

        push_api = SalesforcePushApi(username, password, serverurl, default_where=default_where)

        # Get the target version
        version = push_api.get_package_version_objs("Id = '%s'" % version_id, limit=1)[0]

        if greater_than_version_id:
            # If working with a range of versions, use an inclusive search
            greater_than_version = push_api.get_package_version_objs("Id = '%s'" % greater_than_version_id, limit=1)[0]
            versions = version.get_older_released_version_objs(greater_than_version=greater_than_version)
            included_versions = []
            for include_version in versions:
                included_versions.append(str(include_version.sf_id))
            if not included_versions:
                raise ValueError('No versions found between version id %s and %s' % (version.version_number, greater_than_version.version_number))

            if len(included_versions) == 1:
                push_api.default_where['PackageSubscriber'] += " AND MetadataPackageVersionId = '%s'" % included_versions[0]
            else:
                push_api.default_where['PackageSubscriber'] += " AND MetadataPackageVersionId IN %s" % "('" + "','".join(included_versions) + "')"
        else:
            # If working with a specific version rather than a range, use an exclusive search
            # Add exclusion of all orgs running on newer releases
            newer_versions = version.get_newer_released_version_objs()
            excluded_versions = [str(version.sf_id),]
            for newer in newer_versions:
                excluded_versions.append(str(newer.sf_id))
            if len(excluded_versions) == 1:
                push_api.default_where['PackageSubscriber'] += " AND MetadataPackageVersionId != '%s'" % excluded_versions[0]
            else:
                push_api.default_where['PackageSubscriber'] += " AND MetadataPackageVersionId NOT IN %s" % "('" + "','".join(excluded_versions) + "')"

        orgs = []
        for subscriber in push_api.get_subscribers():
            orgs.append(subscriber['OrgKey'])

        for org in orgs:
            print org
            

    except SystemExit:
        sys.exit(1)            
    except:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print '-'*60
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
        print '-'*60
        sys.exit(2)
