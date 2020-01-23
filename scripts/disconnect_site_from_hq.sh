function site_delete() {
  DASH_API_POD=`kubectl get pod --selector=app=api --no-headers -o custom-columns=:metadata.name`
  MASTER_SYNC_POD=`kubectl get pods --selector=app=master-sync --no-headers -o custom-columns=:metadata.name`
  while ! kubectl exec -it $DASH_API_POD -n default -- bash -c "npm run clear:toggle-master-off"; do sleep 5s; done
  while ! kubectl exec -it $DASH_API_POD -n default -- bash -c "npm run clear:hq"; do sleep 5s; done
  while ! kubectl exec -it $MASTER_SYNC_POD -n default npm run delete:site; do sleep 5s; done
}

site_delete