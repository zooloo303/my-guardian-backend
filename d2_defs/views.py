import requests
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import DefinitionTables
from .serializers import DefinitionTablesSerializer

def update_definition_tables():
    endpoint = "https://www.bungie.net/Platform/Destiny2/Manifest/"
    response = requests.get(endpoint)
    
    if response.status_code != 200:
        return {'error': 'Failed to fetch manifest data'}
    
    manifest_data = response.json()
    version = manifest_data['Response']['version']
    json_world_component_content_paths = manifest_data['Response']['jsonWorldComponentContentPaths']
    
    if 'en' in json_world_component_content_paths:
        tables = json_world_component_content_paths['en']
        for table, url in tables.items():
            json_response = requests.get(f"https://www.bungie.net{url}")
            if json_response.status_code != 200:
                return {'error': f'Failed to fetch data for table {table}'}
            
            json_content = json_response.json()
            DefinitionTables.objects.create(
                version=version,
                language='en',
                table=table,
                content=json_content
            )

    return {'status': 'Definitions updated successfully'}


class UpdateDefinitionTablesView(APIView):

    def get(self, request, *args, **kwargs):
        #find the latest manifest version
        endpoint = "https://www.bungie.net/Platform/Destiny2/Manifest/"
        response = requests.get(endpoint)
        if response.status_code != 200:
            return Response({'error': 'Failed to fetch manifest data'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            manifest_data = response.json()
            version = manifest_data['Response']['version']
            #now read the first entry from the DefinitionTables model and get the version field
            try:
                record = DefinitionTables.objects.first()
                if record.version == version:
                    return Response({'status': 'Definitions already up to date'}, status=status.HTTP_200_OK)
                else:
                    DefinitionTables.objects.all().delete()
                    update_definition_tables()
                    return Response({'status': 'Definitions updated successfully'}, status=status.HTTP_200_OK)
            except DefinitionTables.DoesNotExist:
                pass
    

# class GetTableContentView(APIView):

#     def get(self, request, table_name, *args, **kwargs):
#         try:
#             # Fetch the record from the DefinitionTables model based on the table name
#             record = DefinitionTables.objects.get(table=table_name)
#             serializer = DefinitionTablesSerializer(record)
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         except DefinitionTables.DoesNotExist:
#             return Response({'error': 'Table not found'}, status=status.HTTP_404_NOT_FOUND)
        

class GetTableContentView(APIView):

    def get(self, request, table_name, *args, **kwargs):
        try:
            # Fetch the record from the DefinitionTables model based on the table name
            record = DefinitionTables.objects.get(table=table_name)
            content = record.content
            
            # Check if a hash is provided in the query parameters
            hash_key = request.query_params.get('hash')
            if hash_key:
                # Convert the hash key to an integer
                hash_key = int(hash_key)
                
                # Look for the hash key in the content
                if str(hash_key) in content:
                    return Response(content[str(hash_key)], status=status.HTTP_200_OK)
                else:
                    return Response({'error': 'Hash not found in the table content'}, status=status.HTTP_404_NOT_FOUND)
            
            # If no hash is provided, return the entire content
            return Response(content, status=status.HTTP_200_OK)
        except DefinitionTables.DoesNotExist:
            return Response({'error': 'Table not found'}, status=status.HTTP_404_NOT_FOUND)